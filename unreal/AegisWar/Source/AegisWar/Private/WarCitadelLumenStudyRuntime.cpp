#include "WarCitadelLumenStudyRuntime.h"
#include "HAL/IConsoleManager.h"

void WarCitadelLumenStudyRuntime::ReviewRecipe(TMap<FString,int32>& Values)
{
    Values.Add(TEXT("r.ScreenPercentage"),100);Values.Add(TEXT("r.DynamicRes.OperationMode"),0);
    Values.Add(TEXT("r.ShadowQuality"),5);Values.Add(TEXT("r.Shadow.CSM.MaxCascades"),4);
    Values.Add(TEXT("r.Shadow.MaxResolution"),2048);
    Values.Add(TEXT("r.AntiAliasingMethod"),2);Values.Add(TEXT("r.TemporalAA.Quality"),2);
    Values.Add(TEXT("r.ViewDistanceScale"),1);
}

bool WarCitadelLumenStudyRuntime::Recipe(const FString& Mode,TMap<FString,int32>& Values)
{
    Values.Reset();
    if (Mode!=TEXT("lumen_software") && Mode!=TEXT("lumen_hardware")) return false;
    const bool Hardware=Mode==TEXT("lumen_hardware");
    Values={{TEXT("r.Lumen.DiffuseIndirect.Allow"),1},{TEXT("r.Lumen.Reflections.Allow"),1},
        {TEXT("r.Lumen.FinalGatherMethod"),1},{TEXT("r.Lumen.HardwareRayTracing"),Hardware ? 1 : 0}};
    if (Hardware)
    {
        Values.Add(TEXT("r.Lumen.ScreenProbeGather.HardwareRayTracing"),1);
        Values.Add(TEXT("r.Lumen.Reflections.HardwareRayTracing"),1);
    }
    else
    {
        Values.Add(TEXT("r.Lumen.TraceMeshSDFs"),1);Values.Add(TEXT("r.Lumen.TraceMeshSDFs.Allow"),1);
        Values.Add(TEXT("r.Lumen.ScreenProbeGather.TraceMeshSDFs"),1);
        Values.Add(TEXT("r.Lumen.Reflections.TraceMeshSDFs"),1);
    }
    return true;
}

bool WarCitadelLumenStudyRuntime::PerformanceRecipe(const FString& Mode,TMap<FString,int32>& Values)
{
    Values.Reset();
    if (Mode==TEXT("baseline") || Mode==TEXT("point_shadows_off")) return true;
    if (Mode==TEXT("preview_shadows_off")) Values.Add(TEXT("r.Shadow.UnbuiltPreviewInGame"),0);
    else if (Mode==TEXT("shadows_off")) Values.Add(TEXT("r.ShadowQuality"),0);
    else if (Mode==TEXT("ssgi_off")) Values.Add(TEXT("r.SSGI.Quality"),0);
    else if (Mode==TEXT("reflections_off")) Values.Add(TEXT("r.SSR.Quality"),0);
    else if (Mode==TEXT("shadow_cache_512")) Values.Add(TEXT("r.Shadow.WholeSceneShadowCacheMb"),512);
    else if (Mode==TEXT("shadow_cache_1024")) Values.Add(TEXT("r.Shadow.WholeSceneShadowCacheMb"),1024);
    else if (Mode==TEXT("virtual_shadow_maps")) Values.Add(TEXT("r.Shadow.Virtual.Enable"),1);
    else return false;
    return true;
}

WarCitadelLumenStudyRuntime::FOverride::FOverride()
    : Tag(*FString::Printf(TEXT("WarCitadelLumenStudy_%s"),*FGuid::NewGuid().ToString())) {}
WarCitadelLumenStudyRuntime::FOverride::~FOverride() { Restore(); }

bool WarCitadelLumenStudyRuntime::FOverride::Apply(const TMap<FString,int32>& Values,FString& Error)
{
    Error.Reset();
    if (!IsInGameThread() || !Changed.IsEmpty() || Values.IsEmpty())
    { Error=TEXT("A fresh game-thread diagnostic override is required");return false; }
#if UE_BUILD_SHIPPING
    Error=TEXT("Private lighting diagnostics are unavailable in shipping builds");return false;
#else
    // Check the entire recipe before mutating anything. Higher-priority console
    // settings remain authoritative; this diagnostic never changes startup gates.
    for (const auto& Pair:Values)
    {
        const auto* Variable=IConsoleManager::Get().FindConsoleVariable(*Pair.Key);
        if (!Variable || (Variable->GetFlags() & ECVF_ReadOnly)!=0
            || (Variable->GetFlags() & ECVF_SetByMask)>ECVF_SetByTemp)
        { Error=TEXT("Unavailable or protected diagnostic CVar: ")+Pair.Key;return false; }
    }
    for (const auto& Pair:Values)
    {
        auto* Variable=IConsoleManager::Get().FindConsoleVariable(*Pair.Key);
        Variable->Set(Pair.Value,ECVF_SetByTemp,Tag);Changed.Add(Variable);
        if (Variable->GetInt()!=Pair.Value || (Variable->GetFlags() & ECVF_SetByMask)!=ECVF_SetByTemp)
        { Error=TEXT("Diagnostic CVar did not retain its requested value: ")+Pair.Key;Restore();return false; }
    }
    return true;
#endif
}

void WarCitadelLumenStudyRuntime::FOverride::Restore()
{
    check(IsInGameThread());
    for (auto* Variable:Changed) Variable->Unset(ECVF_SetByTemp,Tag);
    Changed.Reset();
}
