import OpenAI from "openai";
import { v4 as uuidv4 } from 'uuid';
import assert from "assert";
import fs from "fs";

export type ToolImplementation = {
    toolName: string,
    impl: (args: any, toolId: string) => Promise<string>
    convertErrorToString?: (err: any) => string,
    shouldExecuteInParallel?: (input: {
        toolName: string,
        toolArgs: string,
        toolCallId: string,
        allToolCalls: OpenAI.Responses.ResponseFunctionToolCall[]
    }) => boolean
}

type Node = {
    nodeId: string;
    sessionId: string;
    role: "assistant" | "user" | "system" | "function_call" | "developer"
    value: string
    pointingToNode: Node[]
    name: string
    toolName?: string
    toolResult?: any
    toolArgs?: string
    toolCallIteration?: number
}

let rootNodes: Node[] = [];

let sessionIdNameInputMap: Record<string, Record<string, OpenAI.Responses.ResponseInput>> = {};

function getLastNonToolNodeFrom(node: Node): Node {
    if (node.pointingToNode.length === 0) {
        return node;
    }
    let nonToolNode = node.pointingToNode.filter(node => node.role !== "function_call");
    if (nonToolNode.length === 0) {
        // this means there are only function calls left.. 
        return node;
    } else {
        assert(nonToolNode.length === 1, "Only one non-tool node is allowed");
        return getLastNonToolNodeFrom(nonToolNode[0]);
    }
}

// the sawOtherNameInMiddle is used to keep track when the chain is like agent1 -> agent1 -> agent2 -> agent1... in this case,
// if the name is agent1, we will want to return 1 and not 3 cause agent2 is in the middle.
function getNumberOfNodesUntilLastNodeIsFound(name: string, node: Node): { count: number, sawOtherNameInMiddle: boolean } {
    if (node.pointingToNode.length === 0) {
        if (node.name === name) {
            return { count: 1, sawOtherNameInMiddle: false };
        } else {
            return { count: 0, sawOtherNameInMiddle: true };
        }
    }
    let nonToolNode = node.pointingToNode.filter(node => node.role !== "function_call");
    if (nonToolNode.length === 0) {
        if (node.name === name) {
            return { count: 1, sawOtherNameInMiddle: false };
        } else {
            return { count: 0, sawOtherNameInMiddle: true };
        }
    } else {
        assert(nonToolNode.length === 1, "Only one non-tool node is allowed");
        let res = getNumberOfNodesUntilLastNodeIsFound(name, nonToolNode[0]);
        if (res.sawOtherNameInMiddle) {
            return {
                count: res.count,
                sawOtherNameInMiddle: true
            }
        } else {
            return {
                count: res.count + (node.name === name ? 1 : 0),
                sawOtherNameInMiddle: node.name !== name
            }
        }
    }
}

function getNodeForToolCall(toolCallId: string, rootNode: Node): Node | undefined {
    if (rootNode.role === "function_call" && rootNode.value === toolCallId) {
        return rootNode;
    }
    for (const child of rootNode.pointingToNode) {
        let result = getNodeForToolCall(toolCallId, child);
        if (result !== undefined) {
            return result;
        }
    }
    return undefined;
}

export function clearSessionId(sessionId: string) {
    rootNodes = rootNodes.filter(node => node.sessionId !== sessionId);
    delete sessionIdNameInputMap[sessionId];
}

function isInputPrefixSame(previousInput: OpenAI.Responses.ResponseInput, newInput: OpenAI.Responses.ResponseInput): boolean {
    if (previousInput.length >= newInput.length) {
        return false;
    }

    for (let i = 0; i < previousInput.length; i++) {
        let prev = previousInput[i];
        let curr = newInput[i];
        if (prev.type !== curr.type) {
            return false;
        }
        if ((prev.type === "message" && curr.type === "message") || (prev.type === undefined && curr.type === undefined)) {
            if ((prev as any).content !== (curr as any).content || (prev as any).role !== (curr as any).role) {
                return false;
            }
        } else if (prev.type === "function_call" && curr.type === "function_call") {
            if (prev.call_id !== curr.call_id) {
                return false;
            }
        } else if (prev.type === "function_call_output" && curr.type === "function_call_output") {
            if (prev.call_id !== curr.call_id) {
                return false;
            }
        } else {
            throw new Error("Unsupported input type: " + prev.type);
        }

    }
    return true;
}

export async function callLLMWithToolHandling<T extends OpenAI.Responses.Response>(name: string, sessionId: string, toolId: string | undefined, f: (input: OpenAI.Responses.ResponseInput) => Promise<T>, initialInput: OpenAI.Responses.ResponseInput, toolImplementation: ToolImplementation[], maxToolCallIterations: number = 20, nameCount: number | undefined = undefined): Promise<T> {
    if (sessionIdNameInputMap[sessionId] === undefined) {
        sessionIdNameInputMap[sessionId] = {};
    }
    if (sessionIdNameInputMap[sessionId][name] === undefined) {
        sessionIdNameInputMap[sessionId][name] = [...initialInput];
    } else {
        let previousInput = sessionIdNameInputMap[sessionId][name];
        if (isInputPrefixSame(previousInput, initialInput)) {
            sessionIdNameInputMap[sessionId][name] = [...initialInput];
        } else {
            name = name + " (" + (nameCount === undefined ? 1 : nameCount + 1) + ")";
            return callLLMWithToolHandling(name, sessionId, toolId, f, initialInput, toolImplementation, maxToolCallIterations, nameCount === undefined ? 1 : nameCount + 1);
        }
    }
    let inputWithoutToolCalls = initialInput.filter(input => input.type === "message" || input.type === undefined);
    let rootNodeForSessionId = rootNodes.find(node => node.sessionId === sessionId);
    if (!rootNodeForSessionId) {
        assert(inputWithoutToolCalls[0].type === "message" || inputWithoutToolCalls[0].type === undefined, "Initial input must be a message");
        assert(typeof (inputWithoutToolCalls[0] as any).content === "string", "Initial input must be a message with a string content");
        rootNodeForSessionId = {
            nodeId: uuidv4(),
            sessionId: sessionId,
            role: (inputWithoutToolCalls[0] as any).role,
            value: (inputWithoutToolCalls[0] as any).content,
            pointingToNode: [],
            name: name
        }
        rootNodes.push(rootNodeForSessionId);
        writeNodeToFile(rootNodeForSessionId);
    }
    let rootNodeForThisToolCall: Node | undefined = undefined;
    if (toolId !== undefined) {
        let functionCallNode = getNodeForToolCall(toolId, rootNodeForSessionId);
        assert(functionCallNode !== undefined, "Function call node not found");
        if (functionCallNode.pointingToNode.length === 0) {
            assert(inputWithoutToolCalls[0].type === "message" || inputWithoutToolCalls[0].type === undefined, "Initial input must be a message");
            assert(typeof (inputWithoutToolCalls[0] as any).content === "string", "Initial input must be a message with a string content");
            rootNodeForThisToolCall = {
                nodeId: uuidv4(),
                sessionId: sessionId,
                role: (inputWithoutToolCalls[0] as any).role,
                value: (inputWithoutToolCalls[0] as any).content,
                pointingToNode: [],
                name: name
            }
            functionCallNode.pointingToNode.push(rootNodeForThisToolCall);
            writeNodeToFile(rootNodeForSessionId);
        } else {
            assert(functionCallNode.pointingToNode.length === 1, "Only one non-tool node is allowed");
            rootNodeForThisToolCall = functionCallNode.pointingToNode[0];
        }
    } else {
        rootNodeForThisToolCall = rootNodeForSessionId;
    }
    let lastNonToolNode = getLastNonToolNodeFrom(rootNodeForThisToolCall);
    if (lastNonToolNode.name === name) {
        // We assume a one to one mapping between the nodes and the input without tool calls. This means that we assume that the user
        // has added the assistant response to the input message before the tool is called.
        let startI = getNumberOfNodesUntilLastNodeIsFound(name, rootNodeForThisToolCall).count;
        assert(lastNonToolNode.value === (inputWithoutToolCalls[startI - 1] as any).content, "The value of the last node must be the same as the content of the input without tool calls. Did you forget to add the previous iteration's assistant's response to the input message? Alternatively, you can use a different session ID");
        for (let i = startI; i < inputWithoutToolCalls.length; i++) {
            const currInput = inputWithoutToolCalls[i];
            assert(currInput.type === "message" || currInput.type === undefined, "Should never come here");
            assert(typeof (currInput as any).content === "string", "Should never come here");
            let newNode: Node = {
                nodeId: uuidv4(),
                sessionId: sessionId,
                role: (currInput as any).role,
                value: (currInput as any).content,
                pointingToNode: [],
                name: name
            }
            lastNonToolNode.pointingToNode.push(newNode);
            writeNodeToFile(rootNodeForSessionId);
            lastNonToolNode = newNode;
        }
    } else {
        // this is a new agent flow that is starting.
        for (let i = 0; i < inputWithoutToolCalls.length; i++) {
            const currInput = inputWithoutToolCalls[i];
            assert(currInput.type === "message" || currInput.type === undefined, "Should never come here");
            assert(typeof (currInput as any).content === "string", "Should never come here");
            let newNode: Node = {
                nodeId: uuidv4(),
                sessionId: sessionId,
                role: (currInput as any).role,
                value: (currInput as any).content,
                pointingToNode: [],
                name: name
            }
            lastNonToolNode.pointingToNode.push(newNode);
            writeNodeToFile(rootNodeForSessionId);
            lastNonToolNode = newNode;
        }
    }

    let input = initialInput;
    let response: T | undefined;
    let iterationCount = 0;
    while (iterationCount < maxToolCallIterations) {
        iterationCount++;
        response = await f(input);
        let responseContainsToolCalls = false;
        for (let i = 0; i < response.output.length; i++) {
            const toolCall = response.output[i];
            if (toolCall.type === "function_call") {
                responseContainsToolCalls = true;
                input.push({
                    type: "function_call",
                    call_id: toolCall.call_id,
                    id: toolCall.id,
                    status: toolCall.status,
                    name: toolCall.name,
                    arguments: toolCall.arguments
                });
                let newNode: Node = {
                    nodeId: uuidv4(),
                    sessionId: sessionId,
                    role: "function_call",
                    value: toolCall.call_id,
                    pointingToNode: [],
                    name: name,
                    toolName: toolCall.name,
                    toolArgs: toolCall.arguments,
                    toolCallIteration: iterationCount
                }
                lastNonToolNode.pointingToNode.push(newNode);
                writeNodeToFile(rootNodeForSessionId);
            }
        }

        let toolPromises: Promise<void>[] = [];
        for (let i = 0; i < response.output.length; i++) {
            const toolCall = response.output[i];
            if (toolCall.type === "function_call") {
                let toolFound = false;
                for (const tool of toolImplementation) {
                    if (toolCall.name === tool.toolName) {
                        toolFound = true;
                        let shouldExecuteInParallel = false;
                        if (tool.shouldExecuteInParallel) {
                            shouldExecuteInParallel = tool.shouldExecuteInParallel({
                                toolName: toolCall.name,
                                toolArgs: toolCall.arguments,
                                toolCallId: toolCall.call_id,
                                allToolCalls: response.output.filter(output => output.type === "function_call")
                            });
                        }
                        const callId = toolCall.call_id;

                        let p = new Promise<void>(async (resolve, reject) => {
                            try {
                                let output = await tool.impl(!toolCall.arguments ? {} : JSON.parse(toolCall.arguments), toolCall.call_id);
                                input.push({
                                    type: "function_call_output",
                                    call_id: callId,
                                    output: output
                                });
                                for (let i = 0; i < lastNonToolNode.pointingToNode.length; i++) {
                                    if (lastNonToolNode.pointingToNode[i].value === callId) {
                                        lastNonToolNode.pointingToNode[i].toolResult = output;
                                        break;
                                    }
                                }
                            } catch (err) {
                                if (tool.convertErrorToString) {
                                    input.push({
                                        type: "function_call_output",
                                        call_id: callId,
                                        output: "There was an error while calling the tool. Error: " + tool.convertErrorToString(err)
                                    });
                                    for (let i = 0; i < lastNonToolNode.pointingToNode.length; i++) {
                                        if (lastNonToolNode.pointingToNode[i].value === callId) {
                                            lastNonToolNode.pointingToNode[i].toolResult = "There was an error while calling the tool. Error: " + tool.convertErrorToString(err);
                                            break;
                                        }
                                    }
                                } else {
                                    reject(err);
                                }
                            }
                            resolve();
                        });
                        if (!shouldExecuteInParallel) {
                            await p;
                            writeNodeToFile(rootNodeForSessionId);
                        } else {
                            toolPromises.push(p);
                        }
                        break;
                    }
                }
                if (!toolFound) {
                    throw new Error(`Unknown function call: ${toolCall.name}`);
                }
            }
        }
        if (!responseContainsToolCalls) {
            break;
        }
        if (toolPromises.length > 0) {
            await Promise.all(toolPromises);
            writeNodeToFile(rootNodeForSessionId);
        }
    }

    if (!response) {
        throw new Error("No response received from AI after multiple iterations");
    }
    let hasFunctionCall = false;
    for (let i = 0; i < response.output.length; i++) {
        if (response.output[i].type === "function_call") {
            hasFunctionCall = true;
        }
    }
    if (hasFunctionCall) {
        throw new Error("Function call still present even after many iterations!");
    }

    let responseNode: Node = {
        nodeId: uuidv4(),
        sessionId: sessionId,
        role: "assistant",
        value: response.output_text,
        pointingToNode: [],
        name: name
    }
    lastNonToolNode.pointingToNode.push(responseNode);

    writeNodeToFile(rootNodeForSessionId);

    return response;
}

function writeNodeToFile(node: Node) {
    if (process.env.AGENT_GRAPH_SAVE_OUTPUT === "true") {
        let outputDir = process.env.AGENT_GRAPH_OUTPUT_DIR || "./agentgraph_output";
        if (!outputDir.endsWith("/")) {
            outputDir += "/";
        }
        fs.writeFileSync(outputDir + node.sessionId + ".json", JSON.stringify(node, null, 2), { flag: 'w' });
    }
}