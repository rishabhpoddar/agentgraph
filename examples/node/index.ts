import dotenv from "dotenv";
import { OpenAI } from "openai";
import readline from 'readline';
import { v4 as uuidv4 } from 'uuid';
import { callLLMWithToolHandling, clearSessionId } from "@trythisapp/agentgraph";
import { queryDatabase } from './db';
dotenv.config();

const openaiClient = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
});

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

rl.question('Please enter your query: ', async (userInput) => {
    let sessionId = uuidv4();
    console.log(`Session ID: ${sessionId}. File is saved in ./agentgraph_output/${sessionId}.json`);

    await mainAgent(userInput, sessionId);
});

async function mainAgent(userInput: string, sessionId: string) {
    let input: OpenAI.Responses.ResponseInput = [{
        role: "system",
        content: `
You are a helpful assistant for querying a database. You need to  answer the user's query by using the following tools:
- SQLAgent: A tool that converts the natural language query into a SQL query
- databaseAgent: A tool that executes the SQL query and returns the results

Use these tools only if you need to use them.`
    }, {
        role: "user",
        content: userInput
    }];

    try {
        let response = await callLLMWithToolHandling("mainAgent", sessionId, undefined, async (inp) => {
            return await openaiClient.responses.create({
                model: "gpt-4.1",
                input: inp,
                tools: [{
                    type: "function",
                    strict: true,
                    name: "SQLAgent",
                    description: "Use this tool when you need to convert the natural language query into a SQL query",
                    parameters: {
                        type: "object",
                        properties: {
                            query: {
                                type: "string",
                                description: "The natural language query to convert into a SQL query"
                            }
                        },
                        required: ["query"],
                        additionalProperties: false
                    }
                }, {
                    type: "function",
                    strict: true,
                    name: "databaseAgent",
                    description: "Use this tool when you need to execute the SQL query and return the results",
                    parameters: {
                        type: "object",
                        properties: {
                            query: {
                                type: "string",
                                description: "The SQL query to execute. It must be a valid query returned from the SQLAgent tool call."
                            }
                        },
                        required: ["query"],
                        additionalProperties: false
                    }
                }],
            });
        }, input, [{
            toolName: "SQLAgent",
            impl: async ({ query }: { query: string }, toolId: string) => {
                return runSQLAgent(sessionId, toolId, query);
            }
        }, {
            toolName: "databaseAgent",
            impl: async ({ query }: { query: string }) => {
                return runDatabaseAgent(query);
            }
        }]);

        console.log(response.output_text);
    } finally {
        clearSessionId(sessionId);
    }
}

async function runDatabaseAgent(query: string): Promise<string> {
    return queryDatabase(query);
}

async function runSQLAgent(sessionId: string, toolId: string, query: string): Promise<string> {
    let input: OpenAI.Responses.ResponseInput = [{
        role: "system",
        content: `
You are an expert SQLite SQL query generator. You are given a database schema, and a user's request (in natural language), and you need to return the SQL query that will return the results for the user's request.

<Database Schema>
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);
</Database Schema>

<Output format>
Your output must be a JSON containing only the SQL query as a string like so:
\`\`\`
{
    "sqlQuery": "...."
}
\`\`\`
</Output format>
`
    }, {
        role: "user",
        content: query
    }];
    let response = await callLLMWithToolHandling("SQLAgent", sessionId, toolId, async (inp) => {
        return await openaiClient.responses.create({
            model: "gpt-4.1",
            input: inp,
            text: {
                format: {
                    type: "json_schema",
                    name: "sqlQuery",
                    schema: {
                        type: "object",
                        properties: {
                            sqlQuery: { type: "string" }
                        },
                        required: ["sqlQuery"],
                        additionalProperties: false,
                        strict: true
                    }
                }
            }
        });
    }, input, []);

    return response.output_text;
}
