# Compute Architecture

## AI Inference
- **Ollama** runs on Nova, Mira, and Orin
- Models: Qwen 2.5 32B, DeepSeek Coder v2, LLaMA 3.1 70B
- Embeddings: nomic-embed-text via Ollama OpenAI endpoint

## OpenClaw Agents
- **Main** (Jasper): router agent, default model Qwen 2.5 32B
- **Code** agent: DeepSeek Coder v2
- **Deep** agent: LLaMA 3.1 70B

## Resource Allocation
- GPU workloads distributed across nodes
- Model loading managed by Ollama auto-scheduling
