# Ollama Models

## Active Models
| Model | Size | Use Case | Node(s) |
|-------|------|----------|---------|
| qwen2.5:32b-instruct | ~20GB | Default chat/reasoning | All |
| deepseek-coder-v2:latest | ~16GB | Code generation | All |
| llama3.1:70b | ~40GB | Deep reasoning | Nova/Mira |
| nomic-embed-text | ~275MB | Embeddings | All |

## Model Management
```bash
# Pull a model
ollama pull qwen2.5:32b-instruct

# List models
ollama list

# Remove unused
ollama rm <model>
```
