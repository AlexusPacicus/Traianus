# **Dual Boundary Pattern: Deterministic Execution via Binary Verification**

**Date:** 2026-08-03  
**Scope:** TridenGuard/Traianus (MCP Control Plane)

## **1\. The Problem: The Semantic Capability Vulnerability**

Modern Large Language Model (LLM) agent frameworks construct execution flows by processing system instructions, constraints, and untrusted external data within a shared probabilistic context window. Because the natural language engine evaluates both authorization rules and potential exploit payloads semantically, threat actors can bypass boundaries via Indirect Prompt Injections (IDPI) or contextual manipulation.  
**Failure Mode:** Allowing semantic evaluation logic (the LLM) to govern physical execution boundaries results in non-deterministic security, capability laundering, and vulnerability to string-based evasion (e.g., Unicode homoglyphs, null bytes).

## **2\. Core Principle: "Neurons Propose, Rules Dispose"**

The **Dual Boundary Pattern** resolves this by enforcing a strict separation of concerns, mirroring the Harvard Architecture at the execution layer:

> * **The Data Plane (Untrusted/Probabilistic):** LLMs, prompt environments, and parsed external text. This layer proposes actions (tool calls or code refactoring) but holds **zero execution authority**.  
> * **The Control Plane (Trusted/Deterministic):** A pre-compiled, immutable matrix governing execution limits. It intercepts proposals in-flight and verifies them physically at the byte level before authorizing access to host resources.

## **3\. Architecture of the Dual Boundary**

### **3.1 The Immutable Capability Matrix (Nested Tuples)**

Execution constraints are not defined by system prompts or text-based allowlists. They are structured as immutable, mathematically rigorous data structures (nested tuples) loaded before the probabilistic engine operates.  
Every authorized capability is a clause mapping:  
Clause \= (Intent\_Identifier, Target\_Argument, Physical\_Domain, Boundary\_Constraint)

| Component | Definition | TridenGuard Example |
| :---- | :---- | :---- |
| **Intent\_Identifier** | The authorized tool or action class. | REFACTOR, FIX |
| **Target\_Argument** | The parameter dictating the target. | target\_file, Topological\_Grounding |
| **Physical\_Domain** | The host resource subsystem. | AST\_MUTATION, BYTE\_INSPECTION |
| **Boundary\_Constraint** | The absolute physical limit. | Existence within canonical file\_bytes |

### **3.2 Physical and Binary Verification (Byte-Level Governance)**

To eliminate evasions based on character encoding, formatting, or path abstraction, validation logic is reduced to binary and canonical operations:

> * **Filesystem Containment (Path Canonicalization):** Target paths are resolved to their absolute physical location (e.g., resolving all symlinks and relative ../ shifts). The resulting canonical path must mathematically fall within the authorized directory prefix.  
> * **Network Egress Integrity (Punycode):** Outbound domains are converted to low-level Internationalized Domain Name (IDN) Punycode bytes (e.g., xn--...) prior to matching, neutralizing EchoLeak and Unicode homoglyph attacks.  
> * **Literal Grounding (Subsequence Matching):** When verifying code or context existence, target files are read as raw byte streams (read\_bytes()). The grounding quote is encoded to UTF-8 and verified via exact binary subsequence matching (quote\_bytes in file\_bytes).  
> * **Memory Sanitization:** Primitive type checking is enforced, and inputs are scanned for memory termination signatures (e.g., Null Byte \\x00 injection) before processing.

## **4\. Operational Countermeasure: Silent Denial**

When an agent proposal violates a constraint, providing explicit diagnostic errors (e.g., *"Access Denied: Path outside root"*) provides an adversarial feedback loop, allowing the attacker or a compromised LLM to iterate and optimize the exploit payload.  
Instead, the pattern mandates **Silent Denial**:

> 1. The physical host execution is skipped (resources are shielded).  
> 2. A detailed forensic log is appended to an isolated SIEM ledger.  
> 3. The control plane returns a synthetic, benign "Success" or neutral state to the agent context.

This ruptures the feedback loop, as the attacker cannot determine if the exploit was structurally intercepted or simply failed logically.

## **5\. Deployment Context: TridenGuard/Traianus**

| Dimension | TridenGuard/Traianus (Local MCP Server) |
| :---- | :---- |
| **Deployment** | Local Edge/Server via Model Context Protocol (MCP). |
| **Primary Threat Vector** | Unverified codebase mutations and hallucinated refactoring. |
| **Execution Boundary** | JSON-RPC validation before executing mutations. |
| **Binary Verification** | UTF-8 byte subsequence grounding, AST checks. |

