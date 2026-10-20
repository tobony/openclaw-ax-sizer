import marimo

__generated_with = "0.19.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import shutil
    import subprocess
    import zipfile
    from pathlib import Path
    import marimo as mo
    return Path, mo, shutil, subprocess, zipfile


@app.cell
def _(mo):
    mo.md("""
    # OpenClaw & AX Agent Hardware Sizer

    프로젝트 파일 생성, ZIP 패키징, GitHub 공개 저장소 생성 및 GitHub Pages 배포를 관리합니다.

    - 로컬 생성은 `gh` 로그인 없이 실행할 수 있습니다.
    - GitHub 배포는 `gh`와 `git` CLI가 설치되고 `gh auth status`가 통과할 때만 실행됩니다.
    - 모델 속도와 메모리 수치는 추정용 가정값이며 실측 벤치마크가 아닙니다.
    """)
    return


@app.cell
def _(mo):
    project_name = mo.ui.text(value="openclaw-ax-sizer", label="프로젝트 폴더명")
    repo_name = mo.ui.text(value="openclaw-ax-sizer", label="GitHub 저장소명")
    repo_owner = mo.ui.text(value="tobony", label="GitHub 소유자/조직")
    branch = mo.ui.text(value="main", label="기본 브랜치")
    ctx = mo.ui.slider(start=8, stop=128, step=8, value=32, label="시뮬레이터 기본 컨텍스트 (k tokens)")
    ax_default = mo.ui.checkbox(value=True, label="RAG / 임베딩 / Docker 부가 스택 기본 활성화")
    mo.vstack([project_name, repo_name, repo_owner, branch, ctx, ax_default])
    return ax_default, branch, ctx, project_name, repo_name, repo_owner


@app.cell
def _(mo):
    create_btn = mo.ui.run_button(label="프로젝트 파일 및 ZIP 생성")
    deploy_btn = mo.ui.run_button(label="GitHub 공개 저장소 생성 및 Pages 배포")
    mo.hstack([create_btn, deploy_btn], gap=1)
    return create_btn, deploy_btn


@app.cell
def _(Path, ax_default, ctx, create_btn, mo, project_name, zipfile):
    if create_btn.value:
        name = project_name.value.strip()
        if not name or Path(name).name != name or name in {".", ".."}:
            result = mo.callout("프로젝트 폴더명은 단일 폴더명이어야 합니다.", kind="danger")
        else:
            root = Path.cwd() / name
            (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)

            html = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenClaw & AX 에이전트 하드웨어 시뮬레이터</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>input[type=range]{accent-color:#2563eb}</style></head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-4 md:p-8 font-sans">
<main class="max-w-5xl mx-auto space-y-6">
<header class="border-b border-slate-800 pb-5"><p class="text-xs text-blue-400 mb-2">Local LLM & Agent Infrastructure Sizer</p>
<h1 class="text-2xl md:text-3xl font-bold">OpenClaw & AX 에이전트 하드웨어 시뮬레이터</h1>
<p class="text-sm text-slate-400 mt-2">메모리 점유율과 에이전트 응답시간을 비교하는 추정 도구입니다. 결과는 실측 벤치마크가 아닙니다.</p></header>
<section class="grid md:grid-cols-3 gap-4 bg-slate-900 border border-slate-800 rounded-2xl p-5">
<div><label class="block text-xs text-slate-400 mb-2">모델 구성</label><select id="model" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-3">
<option value="q4">27B~32B 4-bit (~17GB)</option><option value="q6" selected>27B~32B 6~8-bit (~26GB)</option><option value="multi">멀티 에이전트 32B+14B (~38GB)</option><option value="large">70B Q4 / 100B+ MoE (~45GB)</option></select><p id="desc" class="text-xs text-slate-400 mt-2"></p></div>
<div><div class="flex justify-between text-xs text-slate-400 mb-2"><label>누적 컨텍스트</label><b id="ctxLabel" class="text-blue-400"></b></div><input id="ctx" type="range" min="8" max="128" step="8" value="__CTX__" class="w-full"><div class="flex justify-between text-xs text-slate-500"><span>8k</span><span>32k</span><span>64k</span><span>128k</span></div></div>
<div><label class="block text-xs text-slate-400 mb-2">부가 스택</label><label class="flex gap-3 items-center bg-slate-950 border border-slate-800 rounded-lg p-3"><input id="ax" type="checkbox" __AX__><span class="text-sm">RAG / 임베딩 / Docker (+6GB)</span></label></div>
</section>
<section class="rounded-xl p-4 border border-blue-800 bg-blue-950/30"><p class="text-xs text-blue-400">시뮬레이션 진단</p><h2 id="verdict" class="font-semibold mt-1"></h2><p id="badge" class="text-xs text-blue-300 mt-2"></p></section>
<section class="bg-slate-900 border border-slate-800 rounded-2xl p-5"><h2 class="font-bold mb-3">① 통합 메모리 점유율 및 스왑 한계</h2><div id="memory" class="space-y-4"></div></section>
<section class="bg-slate-900 border border-slate-800 rounded-2xl p-5"><h2 class="font-bold mb-3">② 에이전트 1턴당 추정 응답 시간</h2><div id="latency" class="space-y-4"></div></section>
<footer class="text-xs text-slate-500">구매 전 실제 모델, 양자화, 런타임, 메모리 사용량과 독립 실측 결과를 확인하세요.</footer></main>
<script>
const M={q4:{w:17,kv:5.5,s:1,d:"4-bit 양자화 모델"},q6:{w:26,kv:7.5,s:.78,d:"6~8-bit 고정밀 구성"},multi:{w:38,kv:9,s:.72,d:"32B 플래너와 14B 코더 동시 상주"},large:{w:45,kv:11,s:.48,d:"대형 모델 구성"}};
const H=[{n:"Mac Studio M4 Max (36GB)",r:36,o:7,p:1150,d:26},{n:"Mac Studio M5 Max (64GB 가정)",r:64,o:7,p:4300,d:39},{n:"Mac Studio M5 Max (128GB 가정)",r:128,o:7,p:4300,d:39},{n:"NVIDIA DGX Spark (128GB)",r:128,o:2,p:7800,d:19}];
function update(){let m=M[model.value],c=+ctx.value,a=ax.checked?6:0;ctxLabel.textContent=(c*1000).toLocaleString()+" tok";desc.textContent=m.d;
memory.innerHTML="";latency.innerHTML="";let oom36=false,oom64=false;
H.forEach(h=>{let kv=m.kv*c/32,u=h.o+m.w+kv+a,sw=u>h.r;if(h.r===36&&sw)oom36=true;if(h.r===64&&sw)oom64=true;
let row=document.createElement("div");row.innerHTML=`<div class="flex flex-wrap justify-between gap-2 text-xs mb-2"><b>${h.n}</b><span class="${sw?'text-rose-400':'text-emerald-400'}">${sw?'용량 초과 / 스왑 위험':`사용 ${u.toFixed(1)} / ${h.r}GB · 여유 ${(h.r-u).toFixed(1)}GB`}</span></div><div class="flex h-6 rounded overflow-hidden bg-slate-950">${[[h.o,'#475569'],[m.w,'#3b82f6'],[kv,'#22d3ee'],[a,'#818cf8']].map(x=>`<div title="${x[0].toFixed(1)}GB" style="width:${x[0]/Math.max(h.r,u)*100}%;background:${x[1]}"></div>`).join('')}</div>`;
memory.appendChild(row);let pen=sw?6.5:1,p=c*1000/(h.p*m.s)*pen,d=400/(h.d*m.s)*pen,total=p+d;
let lr=document.createElement("div");lr.innerHTML=`<div class="flex flex-wrap justify-between gap-2 text-xs mb-2"><b>${h.n}</b><span class="${sw?'text-rose-400':'text-slate-300'}">총 ${total.toFixed(1)}초 (프롬프트 ${p.toFixed(1)}초 + 생성 ${d.toFixed(1)}초)</span></div><div class="flex h-5 rounded overflow-hidden bg-slate-950"><div style="width:${Math.min(p/90*100,75)}%;background:#fbbf24"></div><div style="width:${Math.min(d/90*100,25)}%;background:#34d399"></div></div>`;latency.appendChild(lr);});
if(!oom36&&c<=24){verdict.textContent="현재 설정은 M4 Max 36GB에서도 메모리 여유가 있을 수 있습니다.";badge.textContent="실측 메모리 사용량으로 검증하세요."}else if(oom36&&!oom64){verdict.textContent="36GB 구성은 메모리 한계에 도달할 수 있습니다.";badge.textContent="64GB 이상 구성을 검토하세요."}else{verdict.textContent="대형 모델 또는 긴 컨텍스트입니다.";badge.textContent="128GB급 구성 또는 모델 분리를 검토하세요."}}
["model","ctx","ax"].forEach(id=>document.getElementById(id).addEventListener("input",update));update();
</script></body></html>"""
            html = html.replace("__CTX__", str(int(ctx.value)))
            html = html.replace("__AX__", "checked" if ax_default.value else "")
            readme = """# OpenClaw & AX Agent Hardware Sizer

로컬 LLM 및 OpenClaw 에이전트의 메모리·응답시간을 개략적으로 비교하는 정적 시뮬레이터입니다.

## 사용법
GitHub Pages로 배포하거나 `index.html`을 브라우저에서 직접 여세요. 계산 결과는 추정치이며 실측 벤치마크가 아닙니다.
"""
            workflow = """name: Deploy to GitHub Pages
on:
  push:
    branches: ["main"]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: "pages"
  cancel-in-progress: false
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: "."
      - id: deployment
        uses: actions/deploy-pages@v4
"""
            files = {".nojekyll": "", "README.md": readme, "index.html": html, ".github/workflows/deploy.yml": workflow}
            for rel, content in files.items():
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            archive = Path.cwd() / f"{name}.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                for rel in files:
                    zf.write(root / rel, arcname=rel)
            result = mo.callout(f"생성 완료: `{root}` 및 `{archive}`\n\n필수 파일 {len(files)}개를 생성하고 ZIP에 포함했습니다.", kind="success")
    else:
        result = mo.md("위 버튼을 누르면 프로젝트 폴더와 ZIP 파일을 생성합니다.")
    result
    return


@app.cell
def _(Path, branch, deploy_btn, mo, project_name, repo_name, repo_owner, shutil, subprocess):
    if deploy_btn.value:
        name = project_name.value.strip()
        repo = repo_name.value.strip()
        branch_name = branch.value.strip() or "main"
        root = Path.cwd() / name
        gh, git = shutil.which("gh"), shutil.which("git")
        if not name or Path(name).name != name or not repo or "/" in repo:
            result = mo.callout("프로젝트명과 저장소명을 확인하세요. 저장소명은 단일 이름이어야 합니다.", kind="danger")
        elif not root.is_dir() or not (root / "index.html").exists():
            result = mo.callout("먼저 프로젝트 파일 및 ZIP을 생성하세요.", kind="warn")
        elif not gh or not git:
            result = mo.callout("GitHub 배포에는 `gh`와 `git` CLI가 필요합니다. 로컬 생성은 사용할 수 있습니다.", kind="danger")
        elif subprocess.run([gh, "auth", "status"], capture_output=True, text=True).returncode != 0:
            result = mo.callout("`gh` 로그인이 필요합니다. 터미널에서 `gh auth login` 후 다시 실행하세요.", kind="danger")
        else:
            owner = repo_owner.value.strip()
            repo_slug = f"{owner}/{repo}" if owner else repo
            try:
                subprocess.run([git, "init", "-b", branch_name], cwd=root, check=True, capture_output=True, text=True)
                subprocess.run([git, "add", "."], cwd=root, check=True, capture_output=True, text=True)
                changed = subprocess.run([git, "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
                if changed:
                    subprocess.run([git, "-c", "user.name=OpenClaw AX Sizer", "-c", "user.email=actions@users.noreply.github.com",
                                    "commit", "-m", "Initial commit: OpenClaw AX Sizer"], cwd=root, check=True, capture_output=True, text=True)
                subprocess.run([gh, "repo", "create", repo_slug, "--public", "--source", str(root), "--remote", "origin", "--push"],
                               cwd=root, check=True, capture_output=True, text=True)
                subprocess.run([gh, "api", f"repos/{repo_slug}/pages", "-X", "POST", "-f", "build_type=workflow"],
                               cwd=root, capture_output=True, text=True)
                subprocess.run([git, "push", "-u", "origin", branch_name], cwd=root, capture_output=True, text=True)
                url = f"https://github.com/{repo_slug}"
                pages = f"https://{repo_slug.split('/')[0]}.github.io/{repo_slug.split('/')[-1]}/"
                result = mo.callout(f"저장소 생성 및 푸시 요청 완료: {url}\n\nPages URL(배포 완료 후): {pages}\n\nGitHub Actions 탭에서 첫 배포 상태를 확인하세요.", kind="success")
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or str(exc)).strip()
                result = mo.callout(f"GitHub 작업 실패:\n\n`{detail[-1800:]}`", kind="danger")
    else:
        result = mo.md("GitHub 배포는 위의 배포 버튼을 눌렀을 때만 실행됩니다.")
    result


if __name__ == "__main__":
    app.run()
