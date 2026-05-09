param(
    [string]$Cases = "runs/stage6_public_real/merged_v0_1_public_real_cases.json",
    [string]$OutDir = "runs/stage6_public_real",
    [string]$PredictionPrefix = "predictions_v0_1_public_real",
    [string]$EvalPrefix = "eval_v0_1_public_real",
    [string]$CompareName = "compare_v0_1_public_real_7way"
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
    python -m docfailbench.cli evaluate `
        --cases $Cases `
        --predictions $parser.Prediction `
        --out $parser.Result
}

$compareArgs = @("docfailbench.cli", "compare")
foreach ($parser in $parsers) {
    $compareArgs += @("--results", "$($parser.Label)=$($parser.Result)")
}
$compareArgs += @(
    "--out-json", "$OutDir/$CompareName.json",
    "--out-md", "$OutDir/$CompareName.md"
)

python -m @compareArgs

Write-Host "Wrote $OutDir/$CompareName.md"
