from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
import logging, sys
import warnings
import boto3

bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name='us-west-2')

query = "what is the unusal traffic happenned yersterday"

kb_id = 'ISIKGBQCIB'

'''messages = [
    {"role": "system", "content": "You are a network admin and helps to trouble shoot issue based on the user imput"},
    {"role": "user", "content": query},
]'''
# retrieve api for fetching only the relevant context.
relevant_documents = bedrock_agent_runtime_client.retrieve(
    retrievalQuery= {
        'text': query
    },
    knowledgeBaseId=kb_id,
    retrievalConfiguration= {
        'vectorSearchConfiguration': {
            'numberOfResults': 3 # will fetch top 3 documents which matches closely with the query.
        }
    }
)

rel_docs=relevant_documents["retrievalResults"]
rel_docs1=""
for i in rel_docs:
        rel_docs1 = rel_docs1+(i['content']['text'])+"/n"

messages = [
    {"role": "system", "content": "You are a network admin and helps to trouble shoot issue based on the user imput"},
    {"role": "user", "content": rel_docs1},
]

logging.disable(sys.maxsize)
warnings.filterwarnings("ignore")
model_id = "neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16"

number_gpus = 1
max_model_len = 8192

sampling_params = SamplingParams(temperature=0.6, top_p=0.9, max_tokens=256)

tokenizer = AutoTokenizer.from_pretrained(model_id)

prompts = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)

llm = LLM(model=model_id, tensor_parallel_size=number_gpus, max_model_len=max_model_len)

outputs = llm.generate(prompts, sampling_params)

generated_text = outputs[0].outputs[0].text
print(generated_text)
