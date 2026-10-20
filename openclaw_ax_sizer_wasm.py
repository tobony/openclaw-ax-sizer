import marimo

__generated_with = "0.19.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # OpenClaw & AX 에이전트 하드웨어 시뮬레이터 — WASM

    이 버전은 Python 코드를 브라우저의 WebAssembly(Pyodide) 환경에서 실행합니다.
    서버 측 Python, Git 명령, 파일 생성 기능은 포함하지 않습니다.

    **주의:** 메모리·응답시간은 비교용 추정치이며 실측 벤치마크가 아닙니다.
    """)
    return


@app.cell
def _(mo):
    model_options = {
        "27B~32B 4-bit 경량 (~17GB)": "q4",
        "27B~32B 6~8-bit 고정밀 (~26GB)": "q6",
        "멀티 에이전트 32B + 14B (~38GB)": "multi",
        "70B Q4 / 100B+ MoE (~45GB)": "large",
    }
    model = mo.ui.dropdown(options=model_options, value="q6", label="모델 구성")
    context = mo.ui.slider(start=8, stop=128, step=8, value=32, label="누적 컨텍스트 (k tokens)")
    ax_stack = mo.ui.checkbox(value=True, label="RAG / 임베딩 / Docker 부가 스택 (+6GB)")
    mo.vstack([model, context, ax_stack])
    return ax_stack, context, model


@app.cell
def _(ax_stack, context, model, mo):
    models = {
        "q4": {"weight": 17.0, "kv32": 5.5, "speed": 1.0, "desc": "4-bit 양자화 모델"},
        "q6": {"weight": 26.0, "kv32": 7.5, "speed": 0.78, "desc": "6~8-bit 고정밀 구성"},
        "multi": {"weight": 38.0, "kv32": 9.0, "speed": 0.72, "desc": "32B 플래너 + 14B 코더 동시 상주"},
        "large": {"weight": 45.0, "kv32": 11.0, "speed": 0.48, "desc": "대형 모델 구성"},
    }
    hardware = [
        {"name": "Mac Studio M4 Max (36GB)", "ram": 36.0, "os": 7.0, "prefill": 1150.0, "decode": 26.0},
        {"name": "Mac Studio M5 Max (64GB 가정)", "ram": 64.0, "os": 7.0, "prefill": 4300.0, "decode": 39.0},
        {"name": "Mac Studio M5 Max (128GB 가정)", "ram": 128.0, "os": 7.0, "prefill": 4300.0, "decode": 39.0},
        {"name": "NVIDIA DGX Spark (128GB)", "ram": 128.0, "os": 2.0, "prefill": 7800.0, "decode": 19.0},
    ]
    m = models[model.value]
    kv = m["kv32"] * (context.value / 32.0)
    ax = 6.0 if ax_stack.value else 0.0
    rows = []
    for hw in hardware:
        used = hw["os"] + m["weight"] + kv + ax
        over = used > hw["ram"]
        penalty = 6.5 if over else 1.0
        prefill = (context.value * 1000.0 / (hw["prefill"] * m["speed"])) * penalty
        decode = (400.0 / (hw["decode"] * m["speed"])) * penalty
        rows.append({
            "name": hw["name"],
            "ram": hw["ram"],
            "used": used,
            "free": hw["ram"] - used,
            "over": over,
            "prefill": prefill,
            "decode": decode,
            "total": prefill + decode,
        })
    if rows[0]["over"]:
        verdict = "M4 Max 36GB는 이 설정에서 메모리 한계를 넘을 수 있습니다."
    elif context.value <= 24:
        verdict = "현재 설정은 M4 Max 36GB에서도 메모리 여유가 있을 수 있습니다."
    else:
        verdict = "선택한 모델과 컨텍스트의 메모리 사용량을 확인하세요."
    mo.callout(verdict, kind="warn" if rows[0]["over"] else "info")
    return (rows,)


@app.cell
def _(mo, rows):
    memory_table = [
        {
            "하드웨어": r["name"],
            "통합 메모리": f'{r["ram"]:.0f} GB',
            "추정 사용량": f'{r["used"]:.1f} GB',
            "추정 여유": f'{r["free"]:.1f} GB',
            "상태": "초과 / 스왑 위험" if r["over"] else "용량 내",
        }
        for r in rows
    ]
    mo.md("## 1. 통합 메모리 추정")
    mo.ui.table(memory_table)
    return


@app.cell
def _(mo, rows):
    latency_table = [
        {
            "하드웨어": r["name"],
            "프롬프트 처리": f'{r["prefill"]:.1f} 초',
            "400 토큰 생성": f'{r["decode"]:.1f} 초',
            "총 추정 시간": f'{r["total"]:.1f} 초',
            "스왑 페널티 적용": "예" if r["over"] else "아니오",
        }
        for r in rows
    ]
    mo.md("## 2. 에이전트 1턴당 추정 응답 시간")
    mo.ui.table(latency_table)
    return


if __name__ == "__main__":
    app.run()
