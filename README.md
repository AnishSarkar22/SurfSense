


![new_header](https://github.com/user-attachments/assets/e236b764-0ddc-42ff-a1f1-8fbb3d2e0e65)



# SurfSense
While tools like NotebookLM and Perplexity are impressive and highly effective for conducting research on any topic/query, SurfSense elevates this capability by integrating with your personal knowledge base. It is a highly customizable AI research agent, connected to external sources such as search engines (Tavily), Slack, Linear, Notion, YouTube, GitHub and more to come.


# Video

https://github.com/user-attachments/assets/48142909-6391-4084-b7e8-81da388bb1fc




## Key Features
### 1. Latest

#### 💡 **Idea**: 
Have your own highly customizable private NotebookLM and Perplexity integrated with external sources.
#### 📁 **Multiple File Format Uploading Support**
Save content from your own personal files *(Documents, images and supports **27 file extensions**)* to your own personal knowledge base .
#### 🔍 **Powerful Search**
Quickly research or find anything in your saved content .
#### 💬 **Chat with your Saved Content**
 Interact in Natural Language and get cited answers.
#### 📄 **Cited Answers**
Get Cited answers just like Perplexity.
#### 🔔 **Privacy & Local LLM Support**
Works Flawlessly with Ollama local LLMs.
#### 🏠 **Self Hostable**
Open source and easy to deploy locally.
#### 📊 **Advanced RAG Techniques**
- Supports 150+ LLM's
- Supports 6000+ Embedding Models.
- Supports all major Rerankers (Pinecode, Cohere, Flashrank etc)
- Uses Hierarchical Indices (2 tiered RAG setup).
- Utilizes Hybrid Search (Semantic + Full Text Search combined with Reciprocal Rank Fusion).
- RAG as a Service API Backend.

#### ℹ️ **External Sources**
- Search Engines (Tavily)
- Slack
- Linear
- Notion
- Youtube Videos
- GitHub
- and more to come.....

#### 🔖 Cross Browser Extension
- The SurfSense extension can be used to save any webpage you like.
- Its main usecase is to save any webpages protected beyond authentication.


### 2. Temporarily Deprecated

#### Podcasts 
- The SurfSense Podcast feature is currently being reworked for better UI and stability. Expect it soon.


## FEATURE REQUESTS AND FUTURE


**SurfSense is actively being developed.** While it's not yet production-ready, you can help us speed up the process.

Join the [SurfSense Discord](https://discord.gg/ejRNvftDp9) and help shape the future of SurfSense!



## How to get started?

### PRE-START CHECKS

#### PGVector
Make sure pgvector extension is installed on your machine. Setup Guide https://github.com/pgvector/pgvector?tab=readme-ov-file#installation

#### File Uploading Support
For File uploading you need Unstructured.io API key. You can get it at http://platform.unstructured.io/

#### Auth
SurfSense now only works with Google OAuth. Make sure to set your OAuth Client at https://developers.google.com/identity/protocols/oauth2 . We need client id and client secret for backend. Make sure to enable people api and add the required scopes under data access (openid, userinfo.email, userinfo.profile)

![gauth](https://github.com/user-attachments/assets/80d60fe5-889b-48a6-b947-200fdaf544c1)

#### LLM Observability
One easy way to observe SurfSense Researcher Agent is to use LangSmith. Get its API KEY from https://smith.langchain.com/

**Open AI LLMS**
![openai_langraph](https://github.com/user-attachments/assets/b1f4c7a1-0a66-4d21-9053-2e09a5634f95)


**Ollama LLMS**
![ollama_langgraph](https://github.com/user-attachments/assets/5b6c870e-095c-4368-86e6-f7488e0fca28)


#### Crawler Support
SurfSense currently uses [Firecrawl.py](https://www.firecrawl.dev/) right now. Playwright crawler support will be added soon. 


## Quick Start

### Preferred Method: Docker Setup
The recommended way to run SurfSense is using Docker, which ensures consistent environment across different systems.

1. Make sure you have Docker and Docker Compose installed
2. Follow the detailed instructions in our [Docker Setup Guide](DOCKER_SETUP.md)

```bash
# Start all services with one command
docker-compose up --build
```

---
### Alternative: Manual Setup

### Backend (./surfsense_backend)
This is the core of SurfSense. Before we begin let's look at `.env` variables' that we need to successfully setup SurfSense.

|ENV VARIABLE|DESCRIPTION|
|--|--|
| DATABASE_URL| Your PostgreSQL database connection string. Eg. `postgresql+asyncpg://postgres:postgres@localhost:5432/surfsense`|
| SECRET_KEY| JWT Secret key used for authentication. Should be a secure random string. Eg. `SURFSENSE_SECRET_KEY_123456789`|
| GOOGLE_OAUTH_CLIENT_ID| Google OAuth client ID obtained from Google Cloud Console when setting up OAuth authentication|
| GOOGLE_OAUTH_CLIENT_SECRET| Google OAuth client secret obtained from Google Cloud Console when setting up OAuth authentication|
| NEXT_FRONTEND_URL| URL where your frontend application is hosted. Eg. `http://localhost:3000`|
| EMBEDDING_MODEL| Name of the embedding model to use for vector embeddings. Currently works with Sentence Transformers only. Expect other embeddings soon. Eg. `mixedbread-ai/mxbai-embed-large-v1`|
| RERANKERS_MODEL_NAME| Name of the reranker model for search result reranking. Eg. `ms-marco-MiniLM-L-12-v2`|
| RERANKERS_MODEL_TYPE| Type of reranker model being used. Eg. `flashrank`|
| FAST_LLM| LiteLLM routed Smaller, faster LLM for quick responses. Eg. `openai/gpt-4o-mini`, `ollama/deepseek-r1:8b`|
| STRATEGIC_LLM| LiteLLM routed  Advanced LLM for complex reasoning tasks. Eg. `openai/gpt-4o`, `ollama/gemma3:12b`|
| LONG_CONTEXT_LLM| LiteLLM routed  LLM capable of handling longer context windows. Eg. `gemini/gemini-2.0-flash`, `ollama/deepseek-r1:8b`|
| UNSTRUCTURED_API_KEY| API key for Unstructured.io service for document parsing|
| FIRECRAWL_API_KEY| API key for Firecrawl service for web crawling and data extraction|

IMPORTANT: Since LLM calls are routed through LiteLLM make sure to include API keys of LLM models you are using. For example if you used `openai/gpt-4o` make sure to include OpenAI API Key `OPENAI_API_KEY` or if you use `gemini/gemini-2.0-flash` then you include `GEMINI_API_KEY`.

You can also integrate any LLM just follow this https://docs.litellm.ai/docs/providers

Now once you have everything let's proceed to run SurfSense. 
1. Install `uv` : https://docs.astral.sh/uv/getting-started/installation/
2. Now just run this command to install dependencies i.e `uv sync`
3. That's it. Now just run the `main.py` file using `uv run main.py`. You can also optionally pass `--reload` as an argument to enable hot reloading.
4. If everything worked fine you should see screen like this.

![backend](https://i.ibb.co/542Vhqw/backendrunning.png)

---

### FrontEnd (./surfsense_web)

For local frontend setup just fill out the `.env` file of frontend.

|ENV VARIABLE|DESCRIPTION|
|--|--|
| NEXT_PUBLIC_FASTAPI_BACKEND_URL | Give hosted backend url here. Eg. `http://localhost:8000`|

1. Now install dependencies using `pnpm install`
2. Run it using `pnpm run dev`

You should see your Next.js frontend running at `localhost:3000`

#### Some FrontEnd Screens

**Search Spaces** 

![search_spaces](https://github.com/user-attachments/assets/e254c38c-f937-44b6-9e9d-770db583d099)

**Manage Documents** 
![documents](https://github.com/user-attachments/assets/7001e306-eb06-4009-89c6-8fadfdc3fc4d)

**Research Agent** 

![researcher](https://github.com/user-attachments/assets/fda3e61f-f936-4b66-b565-d84edde44a67)


**Agent Chat** 

![chat](https://github.com/user-attachments/assets/bb352d52-1c6d-4020-926b-722d0b98b491)

---

### Extension (./surfsense_browser_extension)

Extension is in plasmo framework which is a cross browser extension framework. Extension main usecase is to save any webpages protected beyond authentication.

For building extension just fill out the `.env` file of frontend.

|ENV VARIABLE|DESCRIPTION|
|--|--|
| PLASMO_PUBLIC_BACKEND_URL| SurfSense Backend URL eg. "http://127.0.0.1:8000" |

Build the extension for your favorite browser using this guide: https://docs.plasmo.com/framework/workflows/build#with-a-specific-target 

When you load and start the extension you should see a Apu page like this

![ext1](https://github.com/user-attachments/assets/1f042b7a-6349-422b-94fb-d40d0df16c40)



After filling in your SurfSense API key you should be able to use extension now.


![ext2](https://github.com/user-attachments/assets/a9b9f1aa-2677-404d-b0a0-c1b2dddf24a7)


|Options|Explanations|
|--|--|
| Search Space | Search Space to save your dynamic bookmarks.  |
| Clear Inactive History Sessions | It clears the saved content for Inactive Tab Sessions.  |
| Save Current Webpage Snapshot | Stores the current webpage session info into SurfSense history store|
| Save to SurfSense | Processes the SurfSense History Store & Initiates a Save Job |




##  Tech Stack


 ### **BackEnd** 

-  **FastAPI**: Modern, fast web framework for building APIs with Python
  
-  **PostgreSQL with pgvector**: Database with vector search capabilities for similarity searches

-  **SQLAlchemy**: SQL toolkit and ORM (Object-Relational Mapping) for database interactions

-  **Alembic**: A database migrations tool for SQLAlchemy.

-  **FastAPI Users**: Authentication and user management with JWT and OAuth support

-  **LangGraph**: Framework for developing AI-agents.
  
-  **LangChain**: Framework for developing AI-powered applications.

-  **LLM Integration**: Integration with LLM models through LiteLLM

-  **Rerankers**: Advanced result ranking for improved search relevance

-  **Hybrid Search**: Combines vector similarity and full-text search for optimal results using Reciprocal Rank Fusion (RRF)

-  **Vector Embeddings**: Document and text embeddings for semantic search

-  **pgvector**: PostgreSQL extension for efficient vector similarity operations

-  **Chonkie**: Advanced document chunking and embedding library
 - Uses `AutoEmbeddings` for flexible embedding model selection
 -  `LateChunker` for optimized document chunking based on embedding model's max sequence length


  
---
 ### **FrontEnd**

-  **Next.js 15.2.3**: React framework featuring App Router, server components, automatic code-splitting, and optimized rendering.

-  **React 19.0.0**: JavaScript library for building user interfaces.

-  **TypeScript**: Static type-checking for JavaScript, enhancing code quality and developer experience.
- **Vercel AI SDK Kit UI Stream Protocol**: To create scalable chat UI.

-  **Tailwind CSS 4.x**: Utility-first CSS framework for building custom UI designs.

-  **Shadcn**: Headless components library.

-  **Lucide React**: Icon set implemented as React components.

-  **Framer Motion**: Animation library for React.

-  **Sonner**: Toast notification library.

-  **Geist**: Font family from Vercel.

-  **React Hook Form**: Form state management and validation.

-  **Zod**: TypeScript-first schema validation with static type inference.

-  **@hookform/resolvers**: Resolvers for using validation libraries with React Hook Form.

-  **@tanstack/react-table**: Headless UI for building powerful tables & datagrids.



### **Extension** 
 Manifest v3 on Plasmo

## Future Work
- Add More Connectors.
- Patch minor bugs.
- Implement Canvas. 
- Complete Hybrid Search. **[Done]**
- Add support for file uploads QA. **[Done]**
- Shift to WebSockets for Streaming responses. **[Deprecated in favor of AI SDK Stream Protocol]**
- Based on feedback, I will work on making it compatible with local models. **[Done]**
- Cross Browser Extension **[Done]**
- Critical Notifications **[Done | PAUSED]**
- Saving Chats **[Done]**
- Basic keyword search page for saved sessions **[Done]**
- Multi & Single Document Chat **[Done]**



## Contribute 

Contributions are very welcome! A contribution can be as small as a ⭐ or even finding and creating issues.
Fine-tuning the Backend is always desired.

