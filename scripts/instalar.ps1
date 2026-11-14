<#
.SYNOPSIS
    Instalação assistida no Windows: confere tudo o que o projeto precisa, instala o que faltar
    (sempre perguntando antes) e deixa o Ollama aberto com os modelos carregados.

.DESCRIPTION
    Confere, nesta ordem, e mostra um checklist no final:
      1. Sistema: winget, Git e Python 3.11+
      2. Projeto: ambiente virtual (.venv), dependências na versão do pyproject.toml e .env
      3. IA local: Ollama instalado e aberto, modelo de embeddings e modelo de geração,
         com um teste real de cada um (o modelo de geração fica carregado por 30 minutos)
      4. Docker (opcional, só para o caminho Docker): Docker Desktop, Engine e Compose v2
      5. Máquina: memória RAM, disco livre e portas 8000 e 8501

    Tudo é gratuito e nenhuma chave de API é usada. Pode ser rodado quantas vezes quiser:
    o que já estiver certo é só conferido.

.PARAMETER Verificar
    Só audita e mostra o checklist, sem instalar nem alterar nada.

.PARAMETER Sim
    Responde "sim" a todas as perguntas. O Docker só é instalado junto com -ComDocker.

.PARAMETER ComDocker
    Trata o Docker como obrigatório (necessário para gravar o vídeo da entrega).

.PARAMETER Modelo
    Modelo de geração do Ollama. Padrão: LLM_MODEL do .env (qwen2.5:3b).

.PARAMETER Iniciar
    No final, sobe o projeto (scripts\run_local.ps1) sem perguntar.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1 -Verificar
#>
[CmdletBinding()]
param(
    [switch]$Verificar,
    [switch]$Sim,
    [switch]$ComDocker,
    [string]$Modelo = "",
    [switch]$Iniciar
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$OllamaUrl = "http://localhost:11434"
$EmbedModel = "nomic-embed-text"
$SupportedLlms = @("qwen2.5:3b", "llama3.2:3b")
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Results = New-Object System.Collections.Generic.List[object]
$State = @{ Venv = $false; Deps = $false; Ollama = $false; Embed = $false; Llm = $false; Docker = $false }

# --- Utilitários ----------------------------------------------------------------------------
function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host "== $Title" -ForegroundColor Cyan
}

function Add-Result([string]$Item, [string]$Status, [string]$Detail, [string]$Fix = "") {
    $Results.Add([pscustomobject]@{ Status = $Status; Item = $Item; Detail = $Detail; Fix = $Fix })
    $colors = @{ OK = "Green"; AVISO = "Yellow"; FALTA = "Red"; OPCIONAL = "DarkGray" }
    Write-Host ("  [{0,-8}] {1}: {2}" -f $Status, $Item, $Detail) -ForegroundColor $colors[$Status]
}

function Confirm-Step([string]$Question, [switch]$DefaultNo) {
    if ($Verificar) { return $false }
    if ($Sim) { return $true }
    $hint = if ($DefaultNo) { "[s/N]" } else { "[S/n]" }
    $answer = Read-Host "  $Question $hint"
    if ([string]::IsNullOrWhiteSpace($answer)) { return (-not $DefaultNo) }
    return $answer.Trim().ToLower().StartsWith("s")
}

function Update-SessionPath {
    # Programas recém-instalados só entram no PATH de sessões novas; recarrega nesta
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Install-WithWinget([string]$Id, [string]$Name, [string]$Url) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "  winget indisponível: baixe o $Name em $Url, instale e rode este script de novo." -ForegroundColor Yellow
        return $false
    }
    Write-Host "  Instalando $Name pelo winget (pacote $Id, instalador oficial de $Url)..." -ForegroundColor Cyan
    winget install -e --id $Id --accept-source-agreements --accept-package-agreements
    $ok = ($LASTEXITCODE -eq 0)
    Update-SessionPath
    return $ok
}

function Get-EnvValue([string]$Key) {
    foreach ($file in @(".env", ".env.example")) {
        if (Test-Path $file) {
            $line = Select-String -Path $file -Pattern "^\s*$Key\s*=\s*(.+)$" | Select-Object -First 1
            if ($line) { return $line.Matches[0].Groups[1].Value.Trim().Trim('"') }
        }
    }
    return $null
}

function Get-PythonVersion([string]$Exe, [string[]]$PreArgs) {
    try {
        $out = & $Exe @PreArgs -c "import sys; print('%d.%d.%d' % sys.version_info[:3])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return [version](("" + ($out | Select-Object -Last 1)).Trim()) }
    } catch {}
    return $null
}

function Find-Python {
    # Prefere 3.11 (mesma versão do Docker e da CI), depois 3.12; 3.13+ só como último recurso
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidates += [pscustomobject]@{ Exe = "py"; Args = @("-3.11") }
        $candidates += [pscustomobject]@{ Exe = "py"; Args = @("-3.12") }
    }
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { $candidates += [pscustomobject]@{ Exe = $cmd.Source; Args = @() } }
    }
    $found = @()
    foreach ($c in $candidates) {
        $ver = Get-PythonVersion $c.Exe $c.Args
        if ($ver -and $ver -ge [version]"3.11") {
            $found += [pscustomobject]@{ Exe = $c.Exe; Args = $c.Args; Version = $ver }
        }
    }
    $preferred = $found | Where-Object { $_.Version.Minor -le 12 } | Select-Object -First 1
    if ($preferred) { return $preferred }
    return ($found | Select-Object -First 1)
}

function Find-Ollama {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $default = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $default) { return $default }
    return $null
}

function Get-OllamaModels {
    # $null = Ollama fechado; lista (talvez vazia) = Ollama respondendo
    try { $tags = Invoke-RestMethod "$OllamaUrl/api/tags" -TimeoutSec 3 } catch { return $null }
    return , @($tags.models | ForEach-Object { $_.name })
}

function Test-ModelInstalled([object[]]$Installed, [string]$Name) {
    return (($Installed -contains $Name) -or ($Installed -contains "$Name`:latest"))
}

function Start-Ollama([string]$Exe) {
    $app = Join-Path (Split-Path -Parent $Exe) "ollama app.exe"
    if (Test-Path $app) {
        Start-Process -FilePath $app
    } else {
        Start-Process -FilePath $Exe -ArgumentList "serve" -WindowStyle Hidden
    }
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if ($null -ne (Get-OllamaModels)) { return $true }
    }
    return $false
}

function Test-Embedding {
    $body = @{ model = $EmbedModel; input = "search_query: teste" } | ConvertTo-Json
    try {
        $r = Invoke-RestMethod "$OllamaUrl/api/embed" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 120
        return @($r.embeddings[0]).Count
    } catch { return 0 }
}

function Test-Generation([string]$Name) {
    # keep_alive deixa o modelo carregado na memória: a primeira pergunta no sistema já sai rápida
    $body = @{
        model = $Name; prompt = "Responda apenas com a palavra OK."; stream = $false; keep_alive = "30m"
        options = @{ temperature = 0; num_predict = 5 }
    } | ConvertTo-Json
    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        $r = Invoke-RestMethod "$OllamaUrl/api/generate" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 300
        return [pscustomobject]@{ Ok = $true; Seconds = [math]::Round($watch.Elapsed.TotalSeconds, 1); Text = ("" + $r.response).Trim() }
    } catch {
        return [pscustomobject]@{ Ok = $false; Seconds = 0; Text = $_.Exception.Message }
    }
}

function Find-Docker {
    $cmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $default = Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe"
    if (Test-Path $default) { return $default }
    return $null
}

function Get-DockerEngineVersion([string]$Exe) {
    $out = & $Exe info --format "{{.ServerVersion}}" 2>$null
    if ($LASTEXITCODE -eq 0 -and $out) { return ("" + ($out | Select-Object -Last 1)).Trim() }
    return $null
}

Write-Host "Instalação assistida: RAG para documentação técnica" -ForegroundColor Cyan
if ($Verificar) {
    Write-Host "Modo -Verificar: só confere, nada será instalado ou alterado." -ForegroundColor DarkGray
} else {
    Write-Host "O que faltar será instalado só depois da sua confirmação: programas pelo winget, a partir do"
    Write-Host "instalador oficial de cada fabricante; pacotes Python do PyPI; modelos da biblioteca do Ollama."
}

# --- 1. Sistema -------------------------------------------------------------------------------
Write-Section "1. Sistema"
Add-Result "PowerShell" "OK" $PSVersionTable.PSVersion.ToString()

if (Get-Command winget -ErrorAction SilentlyContinue) {
    Add-Result "winget" "OK" "disponível para instalar o que faltar"
} else {
    Add-Result "winget" "AVISO" "ausente: o que faltar terá de ser instalado à mão" "Instale o 'App Installer' pela Microsoft Store"
}

if (Get-Command git -ErrorAction SilentlyContinue) {
    Add-Result "Git" "OK" ((git --version) -replace "git version ", "")
} elseif ((Confirm-Step "Git não encontrado. Instalar agora pelo winget (fonte oficial: git-scm.com)?") -and
    (Install-WithWinget "Git.Git" "Git" "https://git-scm.com/download/win") -and (Get-Command git -ErrorAction SilentlyContinue)) {
    Add-Result "Git" "OK" "instalado agora"
} else {
    Add-Result "Git" "AVISO" "não encontrado (necessário para commits e pull requests)" "winget install -e --id Git.Git"
}

$python = Find-Python
if (-not $python -and -not (Test-Path $VenvPython) -and -not (Get-Command uv -ErrorAction SilentlyContinue)) {
    if ((Confirm-Step "Python 3.11+ não encontrado. Instalar o Python 3.11 pelo winget (fonte oficial: python.org)?") -and
        (Install-WithWinget "Python.Python.3.11" "Python 3.11" "https://www.python.org/downloads/")) {
        $python = Find-Python
    }
}
if ($python -and $python.Version.Minor -le 12) {
    Add-Result "Python" "OK" "$($python.Version) ($($python.Exe) $($python.Args))"
} elseif ($python) {
    Add-Result "Python" "AVISO" "$($python.Version): o projeto é testado no 3.11 (Docker e CI); algumas dependências podem não ter versão para ele" "winget install -e --id Python.Python.3.11"
} elseif (Test-Path $VenvPython) {
    Add-Result "Python" "OK" "nenhum no PATH, mas o .venv já tem o próprio Python"
} elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    Add-Result "Python" "OK" "nenhum no PATH; o uv baixa o Python 3.11 ao criar o .venv"
} else {
    Add-Result "Python" "FALTA" "Python 3.11+ não encontrado" "winget install -e --id Python.Python.3.11 (ou python.org, marcando 'Add python.exe to PATH')"
}

# --- 2. Projeto -------------------------------------------------------------------------------
Write-Section "2. Projeto (.venv, dependências e .env)"
if (-not (Test-Path $VenvPython) -and (Confirm-Step "Criar o ambiente virtual do projeto (pasta .venv, isolada do resto do sistema)?")) {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        & $uv.Source venv .venv --python 3.11
    } elseif ($python) {
        $pyArgs = $python.Args
        & $python.Exe @pyArgs -m venv .venv
    }
}
$venvVersion = $null
if (Test-Path $VenvPython) { $venvVersion = Get-PythonVersion $VenvPython @() }
if ($venvVersion -and $venvVersion -ge [version]"3.11") {
    $State.Venv = $true
    Add-Result "Ambiente virtual" "OK" ".venv com Python $venvVersion"
} elseif ($venvVersion) {
    Add-Result "Ambiente virtual" "FALTA" ".venv com Python $venvVersion (precisa de 3.11+)" "Apague a pasta .venv e rode este script de novo"
} else {
    Add-Result "Ambiente virtual" "FALTA" ".venv não existe" "Rode este script sem -Verificar"
}

if ($State.Venv) {
    $depOutput = & $VenvPython "scripts\verificar_dependencias.py"
    $depOk = ($LASTEXITCODE -eq 0)
    if (-not $depOk) {
        $depOutput | ForEach-Object { Write-Host "      - $_" -ForegroundColor DarkYellow }
        if (Confirm-Step "Instalar as dependências no .venv, do PyPI (pypi.org), nas versões do pyproject.toml?") {
            $uv = Get-Command uv -ErrorAction SilentlyContinue
            if ($uv) {
                & $uv.Source pip install --python $VenvPython -e ".[dev,ui]"
            } else {
                & $VenvPython -m pip --version *> $null
                if ($LASTEXITCODE -ne 0) { & $VenvPython -m ensurepip --upgrade }
                & $VenvPython -m pip install -e ".[dev,ui]"
            }
            $depOutput = & $VenvPython "scripts\verificar_dependencias.py"
            $depOk = ($LASTEXITCODE -eq 0)
        }
    }
    if ($depOk) {
        $State.Deps = $true
        Add-Result "Dependências" "OK" (("" + ($depOutput | Select-Object -Last 1)).Trim())
    } else {
        Add-Result "Dependências" "FALTA" "faltam pacotes ou há versões diferentes do pyproject.toml" "Rode este script sem -Verificar"
    }
} else {
    Add-Result "Dependências" "FALTA" "dependem do .venv" "Rode este script sem -Verificar"
}

if (Test-Path ".env") {
    Add-Result "Arquivo .env" "OK" "presente (nunca vai para o Git)"
} elseif (Confirm-Step "Criar o .env a partir do .env.example?") {
    Copy-Item ".env.example" ".env"
    Add-Result "Arquivo .env" "OK" "criado a partir do .env.example"
} else {
    Add-Result "Arquivo .env" "AVISO" "ausente: valem os valores padrão" "Copy-Item .env.example .env"
}

# --- 3. IA local (Ollama) ---------------------------------------------------------------------
Write-Section "3. IA local (Ollama)"
if (-not $Modelo) { $Modelo = Get-EnvValue "LLM_MODEL" }
if (-not $Modelo) { $Modelo = $SupportedLlms[0] }

$ollamaExe = Find-Ollama
if (-not $ollamaExe -and (Confirm-Step "Ollama não encontrado. Instalar agora pelo winget (gratuito, ~1 GB, fonte oficial: ollama.com)?")) {
    if (Install-WithWinget "Ollama.Ollama" "Ollama" "https://ollama.com/download") { $ollamaExe = Find-Ollama }
}
if ($ollamaExe) {
    Add-Result "Ollama instalado" "OK" $ollamaExe
} else {
    Add-Result "Ollama instalado" "FALTA" "não encontrado: sem ele, o sistema roda só no Modo de Visualização (sem IA)" "winget install -e --id Ollama.Ollama"
}

$models = Get-OllamaModels
if ($null -eq $models -and $ollamaExe -and (Confirm-Step "O Ollama está fechado. Abrir agora?")) {
    Write-Host "  Abrindo o Ollama..." -ForegroundColor Cyan
    if (Start-Ollama $ollamaExe) { $models = Get-OllamaModels }
}
if ($null -ne $models) {
    $State.Ollama = $true
    Add-Result "Ollama em execução" "OK" "respondendo em $OllamaUrl"
} elseif ($ollamaExe) {
    Add-Result "Ollama em execução" "FALTA" "instalado, mas fechado" "Abra o 'Ollama' pelo menu Iniciar"
} else {
    Add-Result "Ollama em execução" "FALTA" "depende da instalação do Ollama" "winget install -e --id Ollama.Ollama"
}

if ($State.Ollama) {
    # Modelo de embeddings
    if ($ollamaExe -and -not (Test-ModelInstalled $models $EmbedModel) -and (Confirm-Step "Baixar o modelo de embeddings '$EmbedModel' (~270 MB, da biblioteca oficial ollama.com/library)?")) {
        & $ollamaExe pull $EmbedModel
        $models = Get-OllamaModels
    }
    if (Test-ModelInstalled $models $EmbedModel) {
        $dims = Test-Embedding
        if ($dims -gt 0) {
            $State.Embed = $true
            Add-Result "Modelo de embeddings" "OK" "$EmbedModel testado ($dims dimensões)"
        } else {
            Add-Result "Modelo de embeddings" "FALTA" "$EmbedModel instalado, mas não respondeu ao teste" "ollama run $EmbedModel"
        }
    } else {
        Add-Result "Modelo de embeddings" "FALTA" "$EmbedModel não baixado" "ollama pull $EmbedModel"
    }

    # Modelo de geração: o configurado; se faltar, aceita outro modelo de 3B suportado já baixado
    $llm = $null
    if (Test-ModelInstalled $models $Modelo) { $llm = $Modelo }
    elseif ($ollamaExe -and (Confirm-Step "Baixar o modelo de geração '$Modelo' (~2 GB, da biblioteca oficial ollama.com/library)?")) {
        & $ollamaExe pull $Modelo
        $models = Get-OllamaModels
        if (Test-ModelInstalled $models $Modelo) { $llm = $Modelo }
    }
    if (-not $llm) {
        $llm = $SupportedLlms | Where-Object { Test-ModelInstalled $models $_ } | Select-Object -First 1
    }
    if ($llm) {
        Write-Host "  Carregando '$llm' na memória (a primeira carga leva de 10 s a 1 min)..." -ForegroundColor Cyan
        $gen = Test-Generation $llm
        if ($gen.Ok) {
            $State.Llm = $true
            $note = if ($llm -ne $Modelo) { "; o .env pede '$Modelo', o run_local.ps1 usará '$llm'" } else { "" }
            Add-Result "Modelo de geração" "OK" "$llm aberto e respondendo ($($gen.Seconds) s, resposta '$($gen.Text)')$note"
        } else {
            Add-Result "Modelo de geração" "FALTA" "$llm não respondeu: $($gen.Text)" "ollama run $llm"
        }
    } else {
        Add-Result "Modelo de geração" "FALTA" "$Modelo não baixado" "ollama pull $Modelo"
    }

    # Modelo de visão (opcional): lê o texto de prints enviados junto com a pergunta
    $visionModel = Get-EnvValue "VISION_MODEL"
    if (-not $visionModel) { $visionModel = "qwen2.5vl:3b" }
    if ($ollamaExe -and -not (Test-ModelInstalled $models $visionModel) -and
        (Confirm-Step "Baixar o modelo de visão '$visionModel' (~3,2 GB, opcional: permite perguntar enviando um print)?")) {
        & $ollamaExe pull $visionModel
        $models = Get-OllamaModels
    }
    if (Test-ModelInstalled $models $visionModel) {
        Add-Result "Modelo de visão" "OK" "$visionModel (perguntas com print)"
    } else {
        Add-Result "Modelo de visão" "OPCIONAL" "$visionModel não baixado: perguntas com print ficam indisponíveis" "ollama pull $visionModel"
    }
} else {
    Add-Result "Modelo de embeddings" "FALTA" "depende do Ollama aberto" "ollama pull $EmbedModel"
    Add-Result "Modelo de geração" "FALTA" "depende do Ollama aberto" "ollama pull $Modelo"
}

# --- 4. Docker (opcional) ---------------------------------------------------------------------
Write-Section "4. Docker (só para o caminho Docker: entrega, vídeo e correção)"
$missing = if ($ComDocker) { "FALTA" } else { "OPCIONAL" }
$dockerExe = Find-Docker
$dockerJustInstalled = $false
if (-not $dockerExe -and ($ComDocker -or -not $Sim)) {
    if ((Confirm-Step "Docker não encontrado. Instalar o Docker Desktop pelo winget (~2 GB, fonte oficial: docker.com; exige reiniciar o Windows)?" -DefaultNo:(-not $ComDocker)) -and
        (Install-WithWinget "Docker.DockerDesktop" "Docker Desktop" "https://www.docker.com/products/docker-desktop/")) {
        Add-Result "Docker Desktop" "AVISO" "instalado agora" "Reinicie o Windows, abra o Docker Desktop e rode este script de novo"
        $dockerExe = $null
        $dockerJustInstalled = $true
    }
}
if ($dockerExe) {
    Add-Result "Docker Desktop" "OK" $dockerExe
    $engine = Get-DockerEngineVersion $dockerExe
    $desktopApp = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not $engine -and (Test-Path $desktopApp) -and (Confirm-Step "O Docker está fechado. Abrir o Docker Desktop?" -DefaultNo:(-not $ComDocker))) {
        Start-Process -FilePath $desktopApp
        Write-Host "  Aguardando o Docker Engine (até 2 minutos)..." -ForegroundColor Cyan
        for ($i = 0; $i -lt 60 -and -not $engine; $i++) {
            Start-Sleep -Seconds 2
            $engine = Get-DockerEngineVersion $dockerExe
        }
    }
    if ($engine) {
        Add-Result "Docker Engine" "OK" "em execução (versão $engine)"
        $compose = & $dockerExe compose version --short 2>$null
        if ($LASTEXITCODE -eq 0 -and $compose) {
            $State.Docker = $true
            Add-Result "Docker Compose" "OK" ("v" + ("" + $compose).Trim().TrimStart("v"))
        } else {
            Add-Result "Docker Compose" $missing "Compose v2 não encontrado" "Atualize o Docker Desktop"
        }
    } else {
        Add-Result "Docker Engine" $missing "parado" "Abra o Docker Desktop e espere 'Engine running'"
    }
} elseif (-not $dockerJustInstalled) {
    Add-Result "Docker Desktop" $missing "não instalado (dispensável para desenvolver no Windows)" "winget install -e --id Docker.DockerDesktop"
}

# --- 5. Máquina -------------------------------------------------------------------------------
Write-Section "5. Máquina"
$ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
if ($ramGb -ge 8) { Add-Result "Memória RAM" "OK" "$ramGb GB" }
else { Add-Result "Memória RAM" "AVISO" "$ramGb GB: o modelo de 3B usa ~2,5 GB; feche outros programas" }

$freeGb = [math]::Round((Get-PSDrive -Name $Root.Substring(0, 1)).Free / 1GB, 1)
if ($freeGb -ge 6) { Add-Result "Disco livre" "OK" "$freeGb GB" }
else { Add-Result "Disco livre" "AVISO" "$freeGb GB: os modelos ocupam ~2,3 GB e as imagens Docker mais ~3 GB" }

foreach ($port in @(8000, 8501)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Add-Result "Porta $port" "AVISO" "em uso (o projeto já está rodando?)" "Feche a janela 'RAG API' ou a interface antes de subir de novo"
    } else {
        Add-Result "Porta $port" "OK" "livre"
    }
}

# --- Checklist final --------------------------------------------------------------------------
Write-Section "Checklist"
$Results | Format-Table -AutoSize -Wrap Status, Item, Detail | Out-String -Width 160 | Write-Host

$pending = @($Results | Where-Object { $_.Status -in @("FALTA", "AVISO") -and $_.Fix })
if ($pending.Count -gt 0) {
    Write-Host "Como resolver o que falta:" -ForegroundColor Yellow
    $shown = @{}
    foreach ($p in $pending) {
        if ($shown.ContainsKey($p.Fix)) { continue }
        $shown[$p.Fix] = $true
        Write-Host "  - $($p.Item): $($p.Fix)"
    }
    Write-Host ""
}

$readyWindows = $State.Venv -and $State.Deps
$readyAi = $State.Ollama -and $State.Embed -and $State.Llm
Write-Host "Resultado:" -ForegroundColor Cyan
if ($readyWindows -and $readyAi) {
    Write-Host "  Caminho Windows: PRONTO, com IA real (Ollama)." -ForegroundColor Green
} elseif ($readyWindows) {
    Write-Host "  Caminho Windows: PRONTO, mas no Modo de Visualização (sem IA). Resolva os itens do Ollama acima." -ForegroundColor Yellow
} else {
    Write-Host "  Caminho Windows: NÃO PRONTO. Resolva os itens marcados como FALTA." -ForegroundColor Red
}
if ($State.Docker) {
    Write-Host "  Caminho Docker:  PRONTO. Comando: docker compose up --build" -ForegroundColor Green
} else {
    Write-Host "  Caminho Docker:  indisponível (opcional para desenvolver; necessário para gravar o vídeo da entrega)." -ForegroundColor DarkGray
}

if ($readyWindows -and -not $Verificar) {
    Write-Host ""
    if ($Iniciar -or (Confirm-Step "Iniciar o projeto agora e validá-lo com duas perguntas de teste?")) {
        & (Join-Path $PSScriptRoot "run_local.ps1") -Testar
        exit $LASTEXITCODE
    }
    Write-Host "Para iniciar depois: powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1"
}

$blocking = @($Results | Where-Object { $_.Status -eq "FALTA" })
if ($blocking.Count -gt 0) { exit 1 }
exit 0
