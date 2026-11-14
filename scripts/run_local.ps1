<#
.SYNOPSIS
    Sobe o projeto na máquina local, sem Docker: ingestão, API (em nova janela) e interface.

.DESCRIPTION
    Caminho Windows. Na primeira vez, rode antes a instalação assistida:
        powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
    O caminho Docker (oficial para a entrega) é: docker compose up --build

    - Qdrant embutido, gravado em disco em .qdrant_local\ (sem servidor).
    - Se o Ollama responder em http://localhost:11434, usa os modelos reais.
    - Senão, entra no modo demonstração: LLM_MODE=mock (respondedor extrativo, que NÃO é
      um LLM) e EMBED_MODE=hash (embeddings por hashing). A interface avisa quando isso ocorre.

.PARAMETER Mock
    Força o modo demonstração mesmo com o Ollama disponível.

.PARAMETER Reindex
    Recria o índice do zero (por padrão, só indexa o que ainda não existe).

.PARAMETER Testar
    Com a API no ar, valida a instalação de ponta a ponta: faz uma pergunta coberta pela
    documentação (precisa responder com citação) e uma fora dela (precisa recusar).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1
#>
[CmdletBinding()]
param(
    [switch]$Mock,
    [switch]$Reindex,
    [switch]$Testar,
    [int]$ApiPort = 8000,
    [int]$UiPort = 8501
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Stop-WithError([string]$Message) { Write-Host "ERRO: $Message" -ForegroundColor Red; exit 1 }

# --- 1. Ambiente virtual -------------------------------------------------------------
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Stop-WithError "Ambiente ainda não instalado. Rode primeiro: powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1"
}
. (Join-Path $Root ".venv\Scripts\Activate.ps1")
Write-Step "Ambiente virtual ativo: $(& $Python --version)"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Step "Criado .env a partir do .env.example"
}

# A API anterior ainda aberta trava a pasta .qdrant_local e a porta
if (Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue) {
    Stop-WithError "Já existe algo escutando na porta $ApiPort. Feche a janela 'RAG API' anterior e rode de novo."
}

# --- 2. Modo de execução ---------------------------------------------------------------
$modeEnv = [ordered]@{
    QDRANT_MODE     = "local"
    QDRANT_PATH     = ".qdrant_local"
    OLLAMA_BASE_URL = "http://localhost:11434"
    API_URL         = "http://localhost:$ApiPort"
}
$ollamaTags = $null
if (-not $Mock) {
    try { $ollamaTags = Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 3 } catch { $ollamaTags = $null }
}
function Test-Installed([string[]]$Installed, [string]$Model) {
    return [bool]($Installed | Where-Object { $_ -eq $Model -or $_ -eq "$Model`:latest" })
}

$llmModel = $null
$embedOk = $false
if ($ollamaTags) {
    $installed = @($ollamaTags.models | ForEach-Object { $_.name })
    $embedOk = Test-Installed $installed "nomic-embed-text"
    # Ordem de preferência: LLM_MODEL do .env/ambiente, depois os modelos de 3B suportados
    $configured = $env:LLM_MODEL
    if (-not $configured -and (Test-Path ".env")) {
        $line = Select-String -Path ".env" -Pattern '^\s*LLM_MODEL\s*=\s*(.+)$' | Select-Object -First 1
        if ($line) { $configured = $line.Matches[0].Groups[1].Value.Trim().Trim('"') }
    }
    foreach ($candidate in @($configured, "llama3.2:3b", "qwen2.5:3b")) {
        if ($candidate -and (Test-Installed $installed $candidate)) { $llmModel = $candidate; break }
    }
}

if ($llmModel -and $embedOk) {
    $modeEnv.LLM_MODE = "ollama"
    $modeEnv.EMBED_MODE = "ollama"
    $modeEnv.LLM_MODEL = $llmModel
    Write-Step "Ollama encontrado: geração com '$llmModel' e embeddings com 'nomic-embed-text'"
} else {
    $modeEnv.LLM_MODE = "mock"
    $modeEnv.EMBED_MODE = "hash"
    if ($Mock) {
        Write-Step "Modo de Visualização (Mock) forçado pela opção -Mock"
    } elseif (-not $ollamaTags) {
        Write-Warning "Ollama não encontrado em localhost:11434: usando o Modo de Visualização (Mock)."
        Write-Warning "Para respostas geradas por IA, rode a instalação assistida: powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1"
    } else {
        if (-not $llmModel) { Write-Warning "Nenhum modelo de geração instalado. Rode: ollama pull qwen2.5:3b" }
        if (-not $embedOk) { Write-Warning "Modelo de embeddings ausente. Rode: ollama pull nomic-embed-text" }
        Write-Warning "Usando o Modo de Visualização (Mock) até os modelos serem baixados."
    }
}
foreach ($key in $modeEnv.Keys) { Set-Item -Path "Env:$key" -Value $modeEnv[$key] }

# --- 3. Ingestão ------------------------------------------------------------------------
Write-Step "Indexando data\raw_docs no Qdrant local (.qdrant_local)"
$ingestArgs = @("-m", "ingestion.cli", "--strategy", "all", "--wait", "10", "--warmup-reranker")
if (-not $Reindex) { $ingestArgs += "--skip-existing" }
& $Python @ingestArgs
if ($LASTEXITCODE -ne 0) { Stop-WithError "A ingestão falhou (veja a mensagem acima)." }

# --- 4. API em nova janela --------------------------------------------------------------
Write-Step "Iniciando a API FastAPI na porta $ApiPort (nova janela 'RAG API')"
$envLine = ($modeEnv.Keys | ForEach-Object { "`$env:$_='$($modeEnv[$_])'" }) -join "; "
$apiCommand = "`$host.UI.RawUI.WindowTitle='RAG API'; Set-Location -LiteralPath '$Root'; $envLine; " +
    ". .\.venv\Scripts\Activate.ps1; " +
    "uvicorn api.main:app --app-dir src --reload --reload-dir src --host 127.0.0.1 --port $ApiPort"
Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $apiCommand)

$deadline = (Get-Date).AddSeconds(90)
$health = $null
while (-not $health -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 1
    try { $health = Invoke-RestMethod "http://localhost:$ApiPort/health" -TimeoutSec 3 } catch { $health = $null }
}
if (-not $health) { Stop-WithError "A API não respondeu em 90 s. Veja os erros na janela 'RAG API'." }
Write-Step "API no ar: status=$($health.status), llm_mode=$($health.llm_mode), docs em http://localhost:$ApiPort/docs"

# --- 4b. Validação de ponta a ponta (opcional) -------------------------------------------------
if ($Testar) {
    Write-Step "Validação: uma pergunta coberta pela documentação e uma fora dela (pode levar até 1 min)"
    $checks = @(
        [pscustomobject]@{ Question = "Como compartilho fixtures entre vários arquivos de teste?"; Refuse = $false },
        [pscustomobject]@{ Question = "O que é HTML?"; Refuse = $true }
    )
    $failed = 0
    foreach ($check in $checks) {
        $body = [Text.Encoding]::UTF8.GetBytes((@{ question = $check.Question } | ConvertTo-Json))
        try {
            $r = Invoke-RestMethod "http://localhost:$ApiPort/ask" -Method Post -ContentType "application/json; charset=utf-8" -Body $body -TimeoutSec 300
        } catch {
            $failed++
            Write-Host "  [FALHA] '$($check.Question)': $($_.Exception.Message)" -ForegroundColor Red
            continue
        }
        $sources = ($r.citations | ForEach-Object { $_.source } | Select-Object -Unique) -join ", "
        if ($check.Refuse -and $r.refused) {
            Write-Host "  [OK] '$($check.Question)': recusou, como esperado ($($r.refusal_reason))" -ForegroundColor Green
        } elseif (-not $check.Refuse -and -not $r.refused -and $sources) {
            Write-Host "  [OK] '$($check.Question)': respondeu citando $sources ($([math]::Round($r.latency_ms / 1000, 1)) s)" -ForegroundColor Green
        } else {
            $failed++
            $expected = if ($check.Refuse) { "recusar" } else { "responder com citação" }
            Write-Host "  [FALHA] '$($check.Question)': deveria $expected (refused=$($r.refused), motivo=$($r.refusal_reason))" -ForegroundColor Red
        }
    }
    if ($failed -eq 0) {
        Write-Step "Instalação validada de ponta a ponta (llm_mode=$($health.llm_mode))."
    } else {
        Write-Warning "$failed teste(s) falharam. Veja os erros na janela 'RAG API'; a interface abre mesmo assim."
    }
}

# --- 5. Interface Streamlit (nesta janela) ---------------------------------------------
$uiUrl = "http://localhost:$UiPort"
# Abre o navegador quando a interface responder (o modo headless evita a pergunta de e-mail
# que o Streamlit faz no terminal na primeira execução)
Start-Job -ArgumentList $uiUrl -ScriptBlock {
    param($url)
    for ($i = 0; $i -lt 60; $i++) {
        try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process $url; break }
        catch { Start-Sleep -Seconds 1 }
    }
} | Out-Null

Write-Step "Abrindo a interface em $uiUrl (Ctrl+C encerra a interface; feche a janela 'RAG API' para parar a API)"
streamlit run src/ui/app.py --server.port $UiPort --server.headless true --browser.gatherUsageStats false
