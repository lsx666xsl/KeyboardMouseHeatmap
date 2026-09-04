param(
    [int]$X = 0, [int]$Y = 0, [int]$W = 0, [int]$H = 0,
    [string]$OutFile = "C:\Users\579\AppData\Local\Temp\kp-shot.png"
)
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
if ($W -le 0) { $W = $b.Width }
if ($H -le 0) { $H = $b.Height }
$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($X, $Y, 0, 0, (New-Object System.Drawing.Size($W, $H)))
$g.Dispose()
$bmp.Save($OutFile, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "SAVED $OutFile ${W}x${H} at ($X,$Y)"
