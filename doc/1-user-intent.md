# 1. User intent detection

Check if a request can be fulfilled, when usure offer alternative, *known good* variations of a question.

## Workflow:

1.  **Intent Detection**: The user's natural language query (e.g., "Show me the companies Philip Shindler has invested in") is first passed to an LLM. The LLM's job here is to understand the user's *intent*. It can classify the query into a predefined category, such as `INVESTMENT_QUERY` or `PERSON_QUERY`. It can also extract key entity "Philipp Schindler" (e.g., using Neo4j full-text search indexes with a fuzzy operator on the `Person` nodes) and "invested in" relation. This way the user's ambiguous question is replaced with a structured request.
2.  **Query Generation**: After identifying the intent and entities, the LLM, with the help of the Neo4j graph schema, generates a *Cypher* query. The LLM is "prompted" with the graph's schema (node labels, relationship types, and properties) to ensure the generated query is valid and executable.
3.  **Feasibility Check & Execution**: The generated *Cypher* query is then executed against the Neo4j knowledge graph. This is where you check if the request can be satisfied.
    * If the query returns results, the request is successful. The data is retrieved.
    * If the query returns no results, or if it's invalid (e.g., it asks for a relationship that doesn't exist in the graph), the system knows the request can't be fulfilled as stated.
4.  **Response Generation and Variances**: This is the final  step.
    * **Successful Query**: The LLM takes the retrieved data from the Neo4j graph and the original user query, and generates a clear, natural language answer. This process is called "grounding" the LLM's response in the factual data from your graph, which significantly reduces the risk of "hallucinations."
    * **Unsuccessful Query**: The system detects the failed query and uses the LLM to propose relevant alternatives based on the existing relationships for "Philipp Schindler" in the graph. The LLM identifies that he has relationships like [:WORKS_AT] and [:MANAGES]. It can then suggest these valid, *known good* queries to the user: Should I look 'Which companies does Philipp Schindler work at?' or 'Which teams does Philipp Schindler manage?'

## Tools and Frameworks

Options:

* **LangChain & LlamaIndex**: They can orchestrate the entire process, from natural language input to Cypher query generation, execution, and final response synthesis. They have specific integrations with Neo4j.
* **Neo4j Labs**: Neo4j itself offers tools and integrations like the **LLM Knowledge Graph Builder** and **NeoConverse**, which are specifically designed to handle these kinds of workflows. They often include features for automatic schema extraction, prompt engineering, and visual interfaces for interacting with the data using natural language.
* **Vector Embeddings**: embedding graph data (nodes and relationships) with vector search can provide additional context. This may helps the LLM with semantic understanding, allowing it to find relevant information even when a user's phrasing is not an exact match.
