# Introduction to RAG (Retrieval-Augmented Generation)

## What is RAG?

Imagine you ask a friend about your college timetable. Your friend does not remember it. So they go to the college notice board. They read the right notice. Then they answer you. RAG works in the same way.

RAG stands for Retrieval-Augmented Generation. It is a way to help an AI chatbot give better answers. The chatbot is powered by an LLM. An LLM (large language model) is a computer program that has read a huge amount of text. It can write text like a human.

An LLM only knows what it read during its training. It does not know your private files. It does not know the news from last week. RAG fixes this. Before the LLM answers, RAG first finds useful information in your own documents. Then it gives that information to the LLM, together with the question. The LLM uses it to write the answer.

So RAG has three simple steps:

1. Retrieve: find the useful information.
2. Augment: add that information to the question.
3. Generate: the LLM writes the answer.

## Why it matters

LLMs are powerful, but they have two big problems.

First, their knowledge is old. An LLM learns from text up to a certain date. After that date, it knows nothing new.

Second, an LLM sometimes makes up facts. It may write an answer that sounds correct but is wrong. This is called a hallucination.

RAG helps with both problems. The answer is based on real documents that you choose. You can add new documents at any time, so the knowledge stays fresh. The chatbot can also show which document it used. Then a person can check the answer.

RAG also lets a company use its private data. For example, a bank can let its chatbot read its own rules. The bank does not need to build a new AI model.

RAG reduces mistakes, but it does not remove them fully. We will see its limits later.

## How it works

RAG has two stages. The first stage happens before any question is asked. The second stage happens every time a user asks a question.

**Stage 1: Prepare the documents**

- Collect the documents. These can be PDFs, web pages or notes. Together they form the knowledge base. A knowledge base is the collection of documents that the system can search.
- Split the documents into chunks. A chunk is a small piece of a document, such as one paragraph. Small pieces are easier to search. This step is called chunking.
- Turn each chunk into an embedding. An embedding is a list of numbers that captures the meaning of a piece of text. Texts with similar meaning get similar numbers.
- Store the embeddings in a vector database. A vector database is a special database that stores these lists of numbers. It can quickly find lists that are close to each other.

**Stage 2: Answer a question**

- Retrieve. The user's question is also turned into an embedding. Then the system does a similarity search. A similarity search finds the chunks whose embeddings are closest to the question's embedding. In other words, it finds the chunks with the most similar meaning. The part of the system that does this is called the retriever.
- Augment. The system takes the best few chunks. It adds them to the prompt. A prompt is the text we send to the LLM. Now the prompt has the question and the useful chunks.
- Generate. The LLM reads the prompt and writes an answer. It uses the chunks as its main source of facts.

Remember one important point. RAG does not change the LLM itself. The model is not trained again. RAG only gives the model better information at the moment it answers.

## A worked example

Let us follow one question from start to end.

Priya studies at a college in Pune. Her college has a chatbot that uses RAG. The college has put its rule book, fee list and exam timetable into the knowledge base.

Priya asks: "What is the last date to pay the exam fee?"

Step 1: Retrieve. The system turns her question into an embedding. It searches the vector database. It finds this chunk from the fee list: "The exam fee must be paid by 20 March. A late fee of 200 rupees applies after this date."

Step 2: Augment. The system builds a prompt. The prompt says: "Answer the student's question using only the text below." Then it adds the chunk and Priya's question.

Step 3: Generate. The LLM reads the prompt. It replies: "The last date to pay the exam fee is 20 March. After that, you must pay a late fee of 200 rupees."

Without RAG, the LLM would not know this college's dates. It might guess a wrong date. With RAG, the answer comes from the college's own document.

Next year, the college may change the date. Then it only updates the fee list. The chatbot gives the new date at once. Nobody needs to train the model again.

## Limits, and RAG compared with fine-tuning

RAG is useful, but it is not perfect.

- If the retriever finds the wrong chunks, the answer will be wrong too.
- If the documents have old or wrong facts, the answer will repeat them.
- The LLM can still make mistakes, even with good chunks.
- An LLM can only read a limited amount of text at one time. This limit is called the context window. So we can add only a few chunks to each prompt.
- Each question needs a search and an LLM call. This takes extra time and money.

People often compare RAG with fine-tuning. Fine-tuning means training an existing model a little more on your own examples. This changes the model itself. Fine-tuning is good for teaching a model a style or a task. RAG is better for giving a model facts that change often. Many teams use both together.

## Key words

- **RAG (Retrieval-Augmented Generation)**: a method where a system first finds useful text in documents. Then it gives that text to an LLM to write an answer.
- **LLM (large language model)**: a computer program trained on a huge amount of text. It can understand and write text.
- **Knowledge base**: the collection of documents that a RAG system can search.
- **Chunk**: a small piece of a document, such as a paragraph. Chunking means splitting documents into chunks.
- **Embedding**: a list of numbers that captures the meaning of a piece of text.
- **Vector database**: a database that stores embeddings and quickly finds similar ones.
- **Similarity search**: a search that finds the chunks with meaning closest to the question.
- **Retriever**: the part of a RAG system that finds the useful chunks.
- **Prompt**: the text we send to an LLM, such as a question with instructions.
- **Hallucination**: when an LLM writes something that sounds true but is false or made up.
- **Context window**: the largest amount of text an LLM can read at one time.
- **Fine-tuning**: training an existing model more on your own examples. This changes the model.

## Recap

- RAG stands for Retrieval-Augmented Generation.
- It has three steps: retrieve, augment and generate.
- First, documents are split into chunks. The chunks are turned into embeddings and stored in a vector database.
- When a user asks a question, the retriever finds the most similar chunks.
- These chunks are added to the prompt. Then the LLM writes the answer.
- RAG keeps answers fresh and based on real documents. It does not train the model again.
- RAG still has limits. Bad chunks or bad documents lead to bad answers.

## Check your understanding

1. What do the three words in RAG stand for?
   **Answer:** Retrieval, Augmented and Generation. The system finds information, adds it to the prompt, and then writes an answer.
2. Why do we split documents into chunks?
   **Answer:** Small pieces are easier to search. Only the most useful pieces are added to the prompt.
3. Does RAG train the LLM again on your documents?
   **Answer:** No. RAG does not change the model. It only gives the model useful text at the time of the question.
4. A company's leave policy changes every year. Should its chatbot use RAG or fine-tuning?
   **Answer:** RAG. The company can simply update the policy document, and the chatbot will use the new facts at once.
