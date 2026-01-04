# RunPod ComfyUI SDXL Mass Image Generation Pipeline

This repository provides a fully reproducible, disposable architecture for generating thousands of images using ComfyUI and SDXL on RunPod.

## Features

- **Reproducible**: Set up in minutes with a single command.
- **Disposable**: Safe to delete after use (0 idle cost).
- **Batch Processing**: Supports 10k+ prompts.
- **Day/Night Variants**: Generates two images per prompt (daytime and nighttime).
- **Resume Support**: Handles interruptions gracefully.
- **Photo-Realistic**: Optimized for street-level photography.

## Prerequisites

- RunPod account
- RunPod template: "Stable Diffusion – ComfyUI" (RTX 3090/4090 recommended)

## Quick Start

1. **Launch Pod**: Start a fresh RunPod pod with the ComfyUI template.

2. **Clone and Run**:
   ```bash
   cd /workspace
   git clone <your-repo-url> sdxl-runpod-pipeline
   cd sdxl-runpod-pipeline
   chmod +x bootstrap.sh
   ./bootstrap.sh
   python3 /workspace/scripts/batch_day_night.py
   ```

3. **Monitor**: Watch the console for progress. Images save to `/workspace/ComfyUI/output/`.

4. **Package Results**:
   ```bash
   cd /workspace/ComfyUI
   zip -r /workspace/outputs.zip output
   ```

5. **Terminate Pod**: Download `outputs.zip` and shut down the pod.

## File Structure

```
sdxl-runpod-pipeline/
├── bootstrap.sh                    # Setup script (installs deps, downloads model, starts ComfyUI)
├── workflows/
│   └── day_night_workflow_api.json # ComfyUI API workflow for day/night generation
├── scripts/
│   └── batch_day_night.py          # Batch processing script
└── jobs/
    ├── prompts.txt                 # Input prompts (one per line)
    └── progress.json               # Resume progress (auto-generated)
```

## Customization

- **Prompts**: Edit `jobs/prompts.txt` with your prompts.
- **Model**: Override `SDXL_NAME` and `SDXL_URL` env vars if needed.
- **Workflow**: Modify `workflows/day_night_workflow_api.json` for custom logic.
- **Suffixes**: Adjust day/night suffixes in `scripts/batch_day_night.py`.

## Troubleshooting

- **ComfyUI not starting**: Check `/workspace/comfyui.log`.
- **Missing files**: Ensure all files are present in the repo.
- **Network issues**: RunPod may block some downloads; use VPN if needed.
- **Out of memory**: Reduce batch size or use higher-end GPU.

## License

MIT License - Use at your own risk.