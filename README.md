# math_conjecturer
Mutli-agent LangGraph system for mathematical open problem proposal 🧠 🚀


## Set up
### Step 0: Clone this repository onto your laptop
***Set up ssh key (optional)***
For ease of future use and security, it is recommended to set up an ssh key for github.
There are many tutorials online, but the easiest way is to probably consult your favorite LLM. See [here](https://gemini.google.com/share/72602dfbb6df) for example.

1. Go to the folder where you would like to save this project
2. Run 
   ```bash 
   git clone git@github.com:SueiWenChen/math_conjecturer.git
   ```
   if you have your ssh key set up; otherwise run 
   ```bash
   git clone https://github.com/SueiWenChen/math_conjecturer.git
   ```
The run `cd math_conjecturer` to move into the folder. Alternatively, open the `math_conjecturer` folder in your code editor or IDE.

###  Step 1: Get your API keys
IMPORTANT: keep you api keys private and do not ever put it into files tracked by git to avoid being compromised.

1. Generate a Google API key in the [Google AI studio](https://aistudio.google.com/api-keys) from "Create API key" --> "Select a cloud project" --> "Create project"
2. Generate an API key for [LangSmith](https://smith.langchain.com) for tracing and debugging. Name your project `math_conjecturer`.
3. Run `cp .env.example .env`  and paste your own API keys inside `.env`.


### Step 2: Installing packages
This project uses `uv` for management. If you have not installed it, run
```bash 
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After that, install the packages by running 
```bash 
uv sync
```


## GUI
First, you may need to manually fix the following code. 
```bash
.venv/lib/chainlit/cache.py
```
and substitute 
```bash
from langchain.cache import SQLiteCache
from langchain.globals import set_llm_cache
```
with
```bash
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
```

First, run 
```bash
uv run chainlit hello
```
to initialize. Then go to `.chainlit/config.toml` and set the variable `latex` to true for latex rendering, and 


```bash
uv run chainlit run app.py -w
```


Also to allow latex rendering allow
```
latex = true
```
in file at location
```angular2html

.chainlit/config.toml
```
