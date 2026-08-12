param(
    [string]$Python = "python",
    [string]$Cases = "data/releases/docfailbench_v0_1_hosted_safe_rc_cases.json",
    [string]$OutDir = "data/releases",
    [string]$PredictionPrefix = "docfailbench_v0_1_hosted_safe_rc_predictions",
    [string]$EvalPrefix = "docfailbench_v0_1_hosted_safe_rc_eval",
    [string]$CompareName = "docfailbench_v0_1_hosted_safe_rc_leaderboard"
)

$ErrorActionPreference = "Stop"

$parsers = @(
    @{ Label = "qwen";      Prediction = "$OutDir/$($PredictionPrefix)_qwen.json";      Result = "$OutDir/$($EvalPrefix)_qwen.json" },
    @{ Label = "plain";     Prediction = "$OutDir/$($PredictionPrefix)_plain.json";     Result = "$OutDir/$($EvalPrefix)_plain.json" },
    @{ Label = "paddleocr"; Prediction = "$OutDir/$($PredictionPrefix)_paddleocr.json"; Result = "$OutDir/$($EvalPrefix)_paddleocr.json" },
    @{ Label = "mineru";    Prediction = "$OutDir/$($PredictionPrefix)_mineru.json";    Result = "$OutDir/$($EvalPrefix)_mineru.json" },
    @{ Label = "marker";    Prediction = "$OutDir/$($PredictionPrefix)_marker.json";    Result = "$OutDir/$($EvalPrefix)_marker.json" },
    @{ Label = "docling";   Prediction = "$OutDir/$($PredictionPrefix)_docling.json";   Result = "$OutDir/$($EvalPrefix)_docling.json" },
    @{ Label = "bbox";      Prediction = "$OutDir/$($PredictionPrefix)_bbox.json";      Result = "$OutDir/$($EvalPrefix)_bbox.json" }
)

foreach ($parser in $parsers) {
    if (-not (Test-Path -LiteralPath $parser.Prediction)) {
        throw "Missing prediction file: $($parser.Prediction)"
    }
    & $Python -m docfailbench.cli evaluate `
        --cases $Cases `
        --predictions $parser.Prediction `
        --out $parser.Result
    if ($LASTEXITCODE -ne 0) {
        throw "Evaluation failed for $($parser.Label)"
    }
}

$compareArgs = @("docfailbench.cli", "compare")
foreach ($parser in $parsers) {
    $compareArgs += @("--results", "$($parser.Label)=$($parser.Result)")
}
$compareArgs += @(
    "--out-json", "$OutDir/$CompareName.json",
    "--out-md", "$OutDir/$CompareName.md"
)
& $Python -m @compareArgs
if ($LASTEXITCODE -ne 0) {
    throw "Hosted-safe comparison failed"
}

Write-Host "Verified $OutDir/$CompareName.md"
