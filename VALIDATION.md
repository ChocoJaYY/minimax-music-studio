# Validation

Date: 2026-10-16. The new protected web UI passed a real CUDA generation on this Windows PC. Focused source/notebook and audio-tool checks passed. A Colab GPU run and live Cloudflare deployment remain separate checks; do not infer them from the Windows result.

## Provenance

The existing Windows installation has already generated MiniMax audio on an RTX 4050 Laptop 6 GB using the pinned official Comfy conversion. This new repo reuses that graph design, with its own app, process lifecycle, prompts, notebook packaging and optional tunnel launcher. Prior installation success does not by itself validate these new components.

The official Hugging Face Space at revision `929e40ed4e425518693ec955ced52aba5ea6c425` was inspected as a design and prompting reference. It uses a full-precision Diffusers pipeline, extra prompt-assistance services and custom streaming/compilation. Those services, credentials, assets and source code were not copied into this repo. This app uses native Comfy nodes and a deterministic brief builder.

## Completed checks

- Six focused tests passed: instrumental conditioning ignores lyric words; invalid/NaN requests fail before GPU work; creative controls reach the native graph; the editing export protects peaks without changing its source or overwriting a result; loops preserve source/length/format; the notebook parses, contains no saved outputs, and embeds exactly the current selected source files.
- A real call through the new password-protected Gradio action generated **4.992 seconds** from a five-second maximum, seed 67891, in **152.26 seconds** including startup. The RTX 4050 6 GB used the existing isolated CUDA 13 backend and verified model files. The original local studio had an idle MiniMax worker loaded; the cross-studio GPU lock correctly refused a second model until that idle worker was released. No editing app was stopped.
- The initial direct resample produced one full-scale sample. The final export function was exercised on the preserved generated FLAC, using a float intermediate and **-0.18968 dB** gain protection. The resulting stereo 48 kHz PCM24 WAV passed finite/non-silent, complete decoding and zero full-scale-sample checks, peak approximately 0.98. Synthetic over-range audio and non-overwrite/source-preservation tests also passed. A second GPU generation was unnecessary for this isolated export change. Evidence: `validation/windows-smoke.json`.
- The existing Cloudflare dashboard route was read: `colab.chocojayy.me → http://localhost:8188`, tunnel down with zero replicas. An existing Cloudflare Access sign-in page is present. No route or access policy was changed.

## Remaining checks

- Actual Colab preparation/generation on its assigned GPU, CUDA stack and system RAM. The Linux worker enables disk-backed loading and disables node-result caching to reduce system-RAM pressure; this is not proof that every free runtime can fit the model.
- Live Cloudflare end-to-end testing on an eligible paid runtime or own GPU host with secrets configured. The free account uses the in-notebook generation form. No tunnel was started from free Colab.
- Colab notebook file upload through the browser extension was blocked because that extension does not have file-URL access. That browser setting was not changed.

The repo was initially private as requested, then the user explicitly changed the requirement to public to avoid granting Colab access to private GitHub repositories. Notebook step 4 now asks for its connection details at runtime using input()/getpass(); no GitHub authorization or Colab Secrets setup is required. No tunnel credential was copied from chat into any file or commit.

No human listening quality, music-theory adherence, loop continuity, or Premiere GUI import should be claimed without a separate review.
