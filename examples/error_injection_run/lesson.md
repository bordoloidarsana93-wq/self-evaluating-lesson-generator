# Introduction to Retrieval‑Augmented Generation (RAG)

## What is RAG
Retrieval‑Augmented Generation (RAG) is a method that helps a **large language model (LLM)** give more accurate answers.  
An LLM is a computer program that can read a prompt and write natural‑language text.  

RAG works in three clear steps:

1. **Retrieve** – find the most relevant pieces of text from a collection of documents.  
2. **Augment** – add those pieces to the prompt together with the user’s question.  
3. **Generate** – the LLM reads the augmented prompt and writes the answer.

## Why it matters
An LLM only knows what was in its training data, up to a fixed date.  
It cannot see new news, recent research, or private company policies.  

LLMs can also **hallucinate**, meaning they may produce text that sounds true but is actually false.  

RAG reduces hallucination by grounding the answer in real documents.  
It also lets the system show the source of each fact, so users can verify the answer.  

A real‑world use case: a customer‑support bot for an e‑commerce site.  
The bot reads the company’s help articles and answers customers with up‑to‑date policies.  

## How it works
Before we describe the two phases, we explain some important words.

A **retriever** is the part that looks for relevant chunks.  
It performs a **similarity search**, which means it compares vectors to find those that are close.  
Closeness is measured with **cosine similarity**.  
The system keeps the best few results, called **top‑k**.  
The LLM can only read a limited amount of text at once; this limit is the **context window**.

RAG has two phases: indexing (done once) and query time (done for each question).

### Indexing phase
1. **Collect documents** – gather PDFs, web pages, or notes. This set is called a **knowledge base**.  
2. **Chunking** – split each document into small pieces called **chunks**. A chunk may be a paragraph or a few hundred words.  
3. **Embedding** – an **embedding model** converts each chunk into an **embedding**, a list of numbers that captures the chunk’s meaning. This list is also called a **vector**.  
4. **Vector database** – store each vector together with its original chunk in a **vector database** (also known as a vector index). The database can quickly find vectors that are close to a query vector.

### Query time phase
1. The user writes a question. The same embedding model turns the question into a query vector.  
2. **Retriever** runs a **similarity search** in the vector database. It measures closeness with **cosine similarity** and returns the **top‑k** most similar chunks (usually 3‑5).  
3. **Augment** – the retrieved chunks are placed into a **prompt**. The prompt also contains the original question and an instruction such as “Answer only using the text below.”  
4. **Generate** – the LLM reads the prompt (which may be up to a limited size called the **context window**) and writes the final answer.

A **token** is a small piece of text that the LLM counts. The context window limits how many tokens the LLM can read at once.

## Worked example
A student in Karnataka asks: “What is the best time to plant mango seedlings in Karnataka?”  

**Step 1 – Retrieve**  
The system searches a local agricultural knowledge base.  
It finds two chunks:  

*Chunk A*: “Mango seedlings should be planted at the beginning of the monsoon, usually June‑July.”  
*Chunk B*: “Soil must be well‑drained and enriched with organic compost before planting.”  

**Step 2 – Augment**  
The system creates a prompt that contains the user’s question, Chunk A, Chunk B, and the instruction “Answer using only the information below.”  

**Step 3 – Generate**  
The LLM reads the prompt and writes:  

“The best time to plant mango seedlings in Karnataka is at the start of the monsoon, around June‑July. Prepare the soil with good drainage and add organic compost before planting.”  

The answer is based on the retrieved facts, not on the LLM’s internal memory.

## Limits, and RAG compared with fine‑tuning
RAG has several limits.  

*If retrieval quality is low, the answer will be low.* Wrong or irrelevant chunks lead to wrong answers.  

*Source quality matters.* Old or inaccurate documents produce inaccurate facts.  

*Chunk size matters.* Very small chunks lose context; very large chunks add noise and may exceed the context window.  

*Context window* restricts how many tokens can be read at once. If we retrieve many chunks, some may be cut off.  

The LLM can still **hallucinate** or misinterpret the retrieved text.  

RAG also adds cost and latency because each query needs an embedding, a search, and an LLM call.  

**RAG vs fine‑tuning**  
Fine‑tuning means training the LLM further on new examples. This changes the model’s internal weights.  

RAG does not retrain or fine‑tune the model. It only retrieves documents and adds them to the prompt at answer time.  

Fine‑tuning is useful for teaching a specific style or task.  
RAG is better for providing up‑to‑date facts or private information.  

Updating knowledge with RAG only requires changing the documents in the knowledge base.  
Updating knowledge with fine‑tuning requires another training run, which is slower and more expensive.  

Both methods can be combined, but they serve different purposes.

## Key words
- **LLM**: a large language model that writes text from a prompt.  
- **Retrieve**: find the most relevant pieces of text from a collection of documents.  
- **Augment**: add the retrieved text to the prompt together with the question.  
- **Generate**: the LLM writes the answer using the retrieved text.  
- **Chunk**: a small piece of a document, such as a paragraph, used for searching.  
- **Chunking**: the process of splitting documents into chunks.  
- **Embedding**: turning text into a list of numbers that capture its meaning.  
- **Vector**: the list of numbers produced by an embedding; it represents meaning.  
- **Vector database**: a storage system that holds vectors and can quickly find similar ones.  
- **Knowledge base**: the collection of documents that RAG searches.  
- **Retriever**: the part of the system that runs the similarity search.  
- **Similarity search**: finding vectors whose meaning is close to the query vector.  
- **Cosine similarity**: a mathematical measure that tells how close two vectors are.  
- **Top‑k**: the number of chunks kept after similarity search.  
- **Prompt**: the text given to the LLM, including question, retrieved chunks, and instructions.  
- **Token**: a small unit of text counted by the LLM.  
- **Context window**: the maximum number of tokens the LLM can read at once.  
- **Hallucination**: when the LLM produces text that is false or made up.  
- **Fine‑tuning**: further training of the LLM that changes its internal weights.  

## Recap
RAG follows three steps: Retrieve, Augment, Generate.  
Retrieve finds relevant chunks from a knowledge base.  
Augment adds those chunks to the prompt.  
Generate lets the LLM write the answer.  

Supporting ideas include chunking, embeddings, vector databases, similarity search, top‑k, context window, and fine‑tuning comparison.

## Check your understanding
1. Which step comes first: retrieving documents or generating the answer?  
   **Answer:** Retrieve comes first.  

2. What is the purpose of a vector database?  
   **Answer:** It stores vectors so the system can quickly find similar ones.  

3. Name one limitation of RAG that can still cause wrong answers.  
   **Answer:** Poor retrieval quality can return irrelevant chunks, leading to wrong answers.  

4. How does RAG differ from fine‑tuning in terms of model changes?  
   **Answer:** RAG does not change the model’s weights; fine‑tuning updates the model itself.
