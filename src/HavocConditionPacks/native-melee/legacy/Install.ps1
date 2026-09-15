param(
    [ValidateSet('Install','Check','Uninstall')][string]$Mode = 'Install',
    [string]$GameDirectory = (Join-Path $PSScriptRoot '../../..'),
    [string]$PackageRoot = (Join-Path $env:APPDATA 'Fatshark/Darktide/HavocConditionManager/diy/packages')
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2

function Safe-Path([string]$Root, [string]$Relative) {
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\','/')
    $path = [IO.Path]::GetFullPath((Join-Path $base $Relative))
    if (-not $path.StartsWith($base + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escapes installation directory.' }
    for ($part = $path; $part; $part = [IO.Path]::GetDirectoryName($part)) {
        if (Test-Path -LiteralPath $part) {
            if ((Get-Item -LiteralPath $part -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked installation paths are not supported: $part" }
        }
    }
    return $path
}
function Hash-File([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create(); $stream = [IO.File]::OpenRead($Path)
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $sha.Dispose() }
}
function Hash-Bytes([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
}
function Write-Atomic([string]$Path, [byte[]]$Bytes) {
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($Path)) | Out-Null
    $temp = $Path + '.hcm-new'
    $stream = [IO.File]::Open($temp, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try { $stream.Write($Bytes, 0, $Bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
    try {
        if (Test-Path -LiteralPath $Path) { [IO.File]::Replace($temp, $Path, [NullString]::Value) }
        else { [IO.File]::Move($temp, $Path) }
    } finally { if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp } }
}
function Write-Json([string]$Path, $Value) { Write-Atomic $Path ([Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 12))) }
function Assert-Stopped { if (Get-Process Darktide -ErrorAction SilentlyContinue) { throw 'Close Darktide before installing or removing animation resources.' } }

# Preserve every unowned database record and its opaque tail byte for byte.
if (-not ('HCMNativeMelee.Database' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
namespace HCMNativeMelee {
 public static class Database {
  static byte[] Read(BinaryReader r, int n) {
   byte[] b=r.ReadBytes(n); if(b.Length!=n)throw new InvalidDataException("Truncated resource database."); return b;
  }
  static string Name(BinaryReader r) {
   uint n=r.ReadUInt32(); if(n>255)throw new InvalidDataException("Invalid resource name.");
   return Encoding.ASCII.GetString(Read(r,(int)n));
  }
  static byte[] Row(string key) {
   using(var m=new MemoryStream())using(var w=new BinaryWriter(m)) {
    w.Write((uint)4);
    foreach(string n in new[]{key+".patch_996",key+".stream.patch_996"}) { byte[] b=Encoding.ASCII.GetBytes(n);w.Write((uint)b.Length);w.Write(b); }
    w.Write(new byte[29]);return m.ToArray();
   }
  }
  static bool Equal(byte[] a,byte[] b) { if(a.Length!=b.Length)return false;for(int i=0;i<a.Length;i++)if(a[i]!=b[i])return false;return true; }
  public static byte[] Transform(byte[] data,string[] keys,bool remove) {
   var wanted=new HashSet<ulong>();foreach(string key in keys)if(!wanted.Add(Convert.ToUInt64(key,16)))throw new InvalidDataException("Duplicate resource key.");
   var found=new HashSet<ulong>();
   using(var input=new MemoryStream(data))using(var r=new BinaryReader(input))
   using(var output=new MemoryStream())using(var w=new BinaryWriter(output)) {
    uint version=r.ReadUInt32(),count=r.ReadUInt32();if(version!=6||count==0||count>100000)throw new InvalidDataException("Unsupported resource database.");
    w.Write(version);w.Write(count);
    for(uint i=0;i<count;i++) {
     ulong key=r.ReadUInt64();uint n=r.ReadUInt32();if(n==0||n>1000)throw new InvalidDataException("Invalid resource variants.");
     bool selected=wanted.Contains(key);string hex=key.ToString("x16");byte[] expected=selected?Row(hex):null;
     var rows=new List<byte[]>();bool existing=false;
     if(selected&&!found.Add(key))throw new InvalidDataException("Duplicate database key.");
     for(uint j=0;j<n;j++) {
      int start=(int)input.Position;if(r.ReadUInt32()!=4)throw new InvalidDataException("Unsupported resource record.");
      string filename=Name(r),streamname=Name(r);Read(r,29);
      int size=(int)input.Position-start;byte[] row=new byte[size];Buffer.BlockCopy(data,start,row,0,size);
      bool ours=selected&&(filename==hex+".patch_996"||streamname==hex+".stream.patch_996");
      if(ours) { if(existing||!Equal(row,expected))throw new InvalidDataException("Animation resource registration conflict.");existing=true;if(remove)continue; }
      rows.Add(row);
     }
     if(selected&&!existing&&!remove)rows.Add(expected);
     if(rows.Count==0)throw new InvalidDataException("Cannot remove the only resource variant.");
     w.Write(key);w.Write((uint)rows.Count);foreach(byte[] row in rows)w.Write(row);
    }
    if(found.Count!=wanted.Count)throw new InvalidDataException("Required enemy resources were not found.");
    w.Write(Read(r,(int)(input.Length-input.Position)));return output.ToArray();
   }
  }
 }
}
'@
}

Assert-Stopped
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Raw | ConvertFrom-Json
$game = [IO.Path]::GetFullPath($GameDirectory)
$database = Safe-Path $game 'bundle/bundle_database.data'
$package = Safe-Path $PackageRoot 'starter-conditions-frenzied_assault'
$stateRoot = [IO.Path]::GetFullPath((Join-Path $PackageRoot '../..'))
$statePath = Safe-Path $stateRoot 'native-melee-installation.json'
$keys = [string[]]@($manifest.patches | ForEach-Object { $_.file.Substring(0,16) })
$databaseBytes = [IO.File]::ReadAllBytes($database)
$databaseHash = Hash-Bytes $databaseBytes

if ($Mode -eq 'Uninstall') {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if ($state.status -ne 'installed' -or $state.game -ne $game) { throw 'No matching completed installation.' }
    $allowed = @{}
    foreach ($patch in $manifest.patches) { $allowed[(Safe-Path $game ('bundle/' + $patch.file))] = $true }
    foreach ($name in $manifest.package_files) { $allowed[(Safe-Path $package $name)] = $true }
    if (@($state.rows).Count -ne $allowed.Count) { throw 'Invalid rollback scope.' }
    $seen = @{}
    foreach ($row in $state.rows) {
        if (-not $allowed.ContainsKey($row.path) -or $seen.ContainsKey($row.path)) { throw 'Invalid rollback path.' }
        $seen[$row.path] = $true
        if ((Hash-File $row.path) -ne $row.new_sha256) { throw "Installed file changed; refusing removal: $($row.path)" }
        if ($row.backup) {
            $original = Safe-Path $stateRoot $row.backup
            if ((Hash-File $original) -ne $row.original_sha256) { throw 'Backup changed; refusing removal.' }
        }
    }
    $clean = [HCMNativeMelee.Database]::Transform($databaseBytes,$keys,$true)
    # Stop referencing the resources before deleting any owned files.
    if ((Hash-File $database) -ne $databaseHash) { throw 'Database changed during removal.' }
    Write-Atomic $database $clean
    foreach ($row in $state.rows) {
        if ($row.backup) { Write-Atomic $row.path ([IO.File]::ReadAllBytes((Safe-Path $stateRoot $row.backup))) }
        else { Remove-Item -LiteralPath $row.path }
    }
    $state.status = 'removed'; Write-Json $statePath $state
    Write-Output 'Frenzied assault animation resources removed. Previous package restored; backups retained.'
    return
}

if ((Hash-File (Safe-Path $game 'binaries/Darktide.exe')) -ne $manifest.executable_sha256) { throw 'This animation pack does not match the installed game version.' }
foreach ($property in $manifest.source_bundles.PSObject.Properties) {
    if ((Hash-File (Safe-Path $game ('bundle/' + $property.Name))) -ne $property.Value) { throw "Game resources changed: $($property.Name)" }
}
$prior = $null; $priorByPath = @{}
if (Test-Path -LiteralPath $statePath) {
    $prior = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if ($prior.status -eq 'installed') {
        if ($prior.game -ne $game) { throw 'A different game installation owns this resource backup.' }
        $allowed = @{}
        foreach ($patch in $manifest.patches) { $allowed[(Safe-Path $game ('bundle/' + $patch.file))] = $true }
        foreach ($name in $manifest.package_files) { $allowed[(Safe-Path $package $name)] = $true }
        if (@($prior.rows).Count -ne $allowed.Count) { throw 'Managed upgrade scope changed; remove the previous installation first.' }
        foreach ($row in $prior.rows) {
            if (-not $allowed.ContainsKey($row.path) -or $priorByPath.ContainsKey($row.path)) { throw 'Invalid managed upgrade path.' }
            if ((Hash-File $row.path) -ne $row.new_sha256) { throw "Installed file changed: $($row.path)" }
            if ($row.backup -and (Hash-File (Safe-Path $stateRoot $row.backup)) -ne $row.original_sha256) { throw 'Backup changed; refusing upgrade.' }
            $priorByPath[$row.path] = $row
        }
        if ([version]$manifest.package_version -lt [version]$prior.package_version) { throw 'Refusing to downgrade managed animation resources.' }
    }
}
$targets = @()
foreach ($patch in $manifest.patches) {
    $source = Safe-Path $PSScriptRoot ('resources/' + $patch.file)
    $target = Safe-Path $game ('bundle/' + $patch.file)
    if ((Hash-File $source) -ne $patch.sha256) { throw 'Animation payload is damaged.' }
    if ((Test-Path -LiteralPath $target) -and (Hash-File $target) -ne $patch.sha256 -and -not $priorByPath.ContainsKey($target)) { throw "Animation patch filename is occupied: $target" }
    $targets += [pscustomobject]@{path=$target;source=$source;is_resource=$true}
}
foreach ($name in $manifest.package_files) {
    $source = Safe-Path $PSScriptRoot ('package/' + $name)
    if ((Hash-File $source) -ne $manifest.package_sha256.$name) { throw "Package payload is damaged: $name" }
    $targets += [pscustomobject]@{path=(Safe-Path $package $name);source=$source;is_resource=$false}
}
if (Test-Path -LiteralPath $package) {
    foreach ($old in Get-ChildItem -LiteralPath $package -Recurse -Force) {
        $relative = $old.FullName.Substring($package.Length+1).Replace('\','/')
        $null = Safe-Path $package $relative
        if (-not $old.PSIsContainer -and $relative -notin $manifest.package_files) { throw "Unknown package file: $relative" }
    }
}
$updated = [HCMNativeMelee.Database]::Transform($databaseBytes,$keys,$false)
if ($priorByPath.Count) {
        if ((Hash-Bytes $updated) -eq $databaseHash -and @($targets | Where-Object { (Hash-File $_.path) -ne (Hash-File $_.source) }).Count -eq 0) {
            Write-Output 'Frenzied assault +20% is already installed; no changes needed.'; return
        }
}
if ($Mode -eq 'Check') { Write-Output 'Checks passed: compatible game, verified animation files, package and resource database. No files changed.'; return }

$backupRelative = 'native-melee-backups/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fffffff')
$backupRoot = Safe-Path $stateRoot $backupRelative
[IO.Directory]::CreateDirectory($backupRoot) | Out-Null
$rows = @(); $undo = @(); $i = 0
foreach ($target in $targets) {
    $exists = Test-Path -LiteralPath $target.path
    $oldHash = $null; $oldBackup = $null
    if ($exists) {
        $oldHash = Hash-File $target.path
        $oldBackup = "$backupRelative/$i.before"
        [IO.File]::Copy($target.path,(Safe-Path $stateRoot $oldBackup))
        if ((Hash-File (Safe-Path $stateRoot $oldBackup)) -ne $oldHash) { throw 'Backup verification failed.' }
    }
    $newHash = Hash-File $target.source
    $undo += [pscustomobject]@{path=$target.path;backup=$oldBackup;old_hash=$oldHash;new_hash=$newHash}
    # Identical experimental resource patches are adopted as owned files.
    $restoreBackup = $oldBackup
    $restoreHash = $oldHash
    if ($target.is_resource) { $restoreBackup=$null }
    if ($priorByPath.ContainsKey($target.path)) {
        # Uninstall still restores the original pre-install package, not an
        # intermediate release. The immediate backup above is for failed-upgrade rollback.
        $restoreBackup = $priorByPath[$target.path].backup
        $restoreHash = $priorByPath[$target.path].original_sha256
    }
    $rows += [pscustomobject]@{path=$target.path;backup=$restoreBackup;original_sha256=$restoreHash;new_sha256=$newHash}
    $i++
}
[IO.File]::WriteAllBytes((Join-Path $backupRoot 'database.before'),$databaseBytes)
$state = [pscustomobject]@{status='prepared';game=$game;package_version=$manifest.package_version;rows=$rows;backup=$backupRelative}
Write-Json (Join-Path $backupRoot 'installation.json') $state
$written = @(); $dbWritten = $false
try {
    Assert-Stopped
    for ($i=0; $i -lt $targets.Count; $i++) {
        $target=$targets[$i]; $old=$undo[$i]
        $actual=$null;if(Test-Path -LiteralPath $target.path){$actual=Hash-File $target.path}
        if ($actual -ne $old.old_hash) { throw 'Concurrent installation file change.' }
        if ($actual -ne $old.new_hash) { Write-Atomic $target.path ([IO.File]::ReadAllBytes($target.source)); $written += $old }
    }
    if ((Hash-File $database) -ne $databaseHash) { throw 'Concurrent database change.' }
    if ((Hash-Bytes $updated) -ne $databaseHash) { Write-Atomic $database $updated; $dbWritten=$true }
    foreach ($row in $rows) { if ((Hash-File $row.path) -ne $row.new_sha256) { throw 'Installed file verification failed.' } }
    $state.status='installed'
    Write-Json (Join-Path $backupRoot 'installation.json') $state
    Write-Json $statePath $state
} catch {
    if ($dbWritten -and (Hash-File $database) -eq (Hash-Bytes $updated)) { Write-Atomic $database $databaseBytes }
    [array]::Reverse($written)
    foreach ($old in $written) {
        if ((Hash-File $old.path) -eq $old.new_hash) {
            if ($old.backup) { Write-Atomic $old.path ([IO.File]::ReadAllBytes((Safe-Path $stateRoot $old.backup))) }
            else { Remove-Item -LiteralPath $old.path }
        }
    }
    throw
}
Write-Output 'Frenzied assault +20% installed. Start Darktide and begin a new solo/bot mission. Backups retained.'
