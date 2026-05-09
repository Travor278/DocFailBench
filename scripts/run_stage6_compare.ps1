param(
    [string]$Cases = "data/releases/docfailbench_v0_1_diagnostic_cases.json",
    [string]$OutDir = "runs/stage6_annotation",
    [switch]$Batch2Only
)

$ErrorActionPreference = "Stop"

if ($Batch2Only) {
    $Cases = "runs/stage6_annotation/imported_human_batch2_cases.json"
    $suffix = "batch2"
    $predictionPrefix = "predictions_batch2"
    $compareName = "compare_batch2_7way"
} else {
    $suffix = "human_batch1_batch2"
    $predictionPrefix = "predictions_human_batch1_batch2"
    $compareName = "compare_human_batch1_batch2_7way"
}

$parsers = @(
    @{ Label = "qwen";      Prediction = "$OutDir/$($predictionPrefix)_qwen.json";      Result = "$OutDir/eval_$($suffix)_qwen.json" },
    @{ Label = "plain";     Prediction = "$OutDir/$($predictionPrefix)_plain.json";     Result = "$OutDir/eval_$($suffix)_plain.json" },
    @{ Label = "paddleocr"; Prediction = "$OutDir/$($predictionPrefix)_paddleocr.json"; Result = "$OutDir/eval_$($suffix)_paddleocr.json" },
    @{ Label = "mineru";    Prediction = "$OutDir/$($predictionPrefix)_mineru.json";    Result = "$OutDir/eval_$($suffix)_mineru.json" },
    @{ Label = "marker";    Prediction = "$OutDir/$($predictionPrefix)_marker.json";    Result = "$OutDir/eval_$($suffix)_marker.json" },
    @{ Label = "docling";   Prediction = "$OutDir/$($predictionPrefix)_docling.json";   Result = "$OutDir/eval_$($suffix)_docling.json" },
    @{ Label = "bbox";      Prediction = "$OutDir/$($predictionPrefix)_bbox.json";      Result = "$OutDir/eval_$($suffix)_bbox.json" }
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

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
    "--out-json", "$OutDir/$compareName.json",
    "--out-md", "$OutDir/$compareName.md"
)

python -m @compareArgs

Write-Host "Wrote $OutDir/$compareName.md"
