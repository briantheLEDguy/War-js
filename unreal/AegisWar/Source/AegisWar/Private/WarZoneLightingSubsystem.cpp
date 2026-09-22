#include "WarZoneLightingSubsystem.h"
#include "WarZoneAnchor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/PostProcessComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "EngineUtils.h"

bool UWarZoneLightingSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{ return Type == EWorldType::Game || Type == EWorldType::PIE || Type == EWorldType::Editor || Type == EWorldType::EditorPreview; }
void UWarZoneLightingSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    AddedHandle = FWorldDelegates::LevelAddedToWorld.AddUObject(this, &ThisClass::LevelChanged);
    RemovedHandle = FWorldDelegates::LevelRemovedFromWorld.AddUObject(this, &ThisClass::LevelChanged);
}
void UWarZoneLightingSubsystem::LevelChanged(ULevel* Level, UWorld* World)
{ if (World == GetWorld()) bEnvironmentDirty = true; }
TStatId UWarZoneLightingSubsystem::GetStatId() const
{ RETURN_QUICK_DECLARE_CYCLE_STAT(UWarZoneLightingSubsystem, STATGROUP_Tickables); }
void UWarZoneLightingSubsystem::Tick(float DeltaTime)
{
    UWorld* World = GetWorld();
    if (!World->IsGameWorld() || !World->HasBegunPlay() || World->GetNetMode() == NM_DedicatedServer) return;
    if (World->GetTimeSeconds() < NextUpdateAt) return;
    NextUpdateAt = World->GetTimeSeconds() + .2;
    for (auto It = World->GetPlayerControllerIterator(); It; ++It)
    {
        auto* Player = It->Get();
        if (!Player || !Player->IsLocalController() || !Player->GetPawn()) continue;
        // Pawn position is authoritative for zone identity; a portal approach camera may extend outside its bounds.
        const auto* Anchor = AWarZoneAnchor::FindAt(World, Player->GetPawn()->GetActorLocation());
        if (Anchor && (Anchor->ZoneId != ActiveZone || bEnvironmentDirty)) Apply(Anchor->ZoneId, Anchor->ZoneOrigin);
        break;
    }
}

bool UWarZoneLightingSubsystem::CreateEnvironment()
{
    if (Sun && Fill && Fog && Sky && Ambient && Grade) return true;
    FActorSpawnParameters Params; Params.ObjectFlags |= RF_Transient;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Sun = GetWorld()->SpawnActor<ADirectionalLight>(Params);
    Fill = GetWorld()->SpawnActor<ADirectionalLight>(Params);
    Fog = GetWorld()->SpawnActor<AExponentialHeightFog>(Params);
    Sky = GetWorld()->SpawnActor<ASkyAtmosphere>(Params);
    Ambient = GetWorld()->SpawnActor<ASkyLight>(Params);
    GradeActor = GetWorld()->SpawnActor<AActor>(Params);
    if (!Sun || !Fill || !Fog || !Sky || !Ambient || !GradeActor) return false;
    for (AActor* Actor : TArray<AActor*>{Sun.Get(), Fill.Get(), Fog.Get(), Sky.Get(), Ambient.Get(), GradeActor.Get()})
    { Actor->SetReplicates(false); Actor->Tags.Add(TEXT("WarLocalZoneEnvironment")); }
    Sun->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    Fill->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    Fog->GetComponent()->SetMobility(EComponentMobility::Movable);
    Ambient->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    Ambient->GetLightComponent()->SetRealTimeCaptureEnabled(true);
    CastChecked<UDirectionalLightComponent>(Sun->GetLightComponent())->SetAtmosphereSunLight(true);
    CastChecked<UDirectionalLightComponent>(Sun->GetLightComponent())->SetAtmosphereSunLightIndex(0);
    // Fog, water and forward translucency select one directional light by priority.
    CastChecked<UDirectionalLightComponent>(Sun->GetLightComponent())->SetForwardShadingPriority(1);
    CastChecked<UDirectionalLightComponent>(Fill->GetLightComponent())->SetAtmosphereSunLight(false);
    CastChecked<UDirectionalLightComponent>(Fill->GetLightComponent())->SetForwardShadingPriority(0);
    Fill->GetLightComponent()->SetCastShadows(false);
    Fog->GetComponent()->SetVolumetricFog(false);
    Fog->GetComponent()->SetFogMaxOpacity(.75f);
    Grade = NewObject<UPostProcessComponent>(GradeActor, NAME_None, RF_Transient);
    GradeActor->AddInstanceComponent(Grade); GradeActor->SetRootComponent(Grade);
    Grade->bUnbound = true; Grade->Priority = 100; Grade->BlendWeight = 1;
    Grade->RegisterComponent();
    return true;
}

void UWarZoneLightingSubsystem::HideAuthoredEnvironment()
{
    const auto Hide = [this](USceneComponent* Component) {
        if (!Component || Component->GetOwner()->ActorHasTag(TEXT("WarLocalZoneEnvironment"))) return;
        if (!AuthoredVisibility.Contains(Component)) AuthoredVisibility.Add(Component, Component->IsVisible());
        Component->SetVisibility(false);
    };
    for (TActorIterator<ADirectionalLight> It(GetWorld()); It; ++It) Hide(It->GetLightComponent());
    for (TActorIterator<ASkyLight> It(GetWorld()); It; ++It) Hide(It->GetLightComponent());
    for (TActorIterator<AExponentialHeightFog> It(GetWorld()); It; ++It) Hide(It->GetComponent());
    for (TActorIterator<ASkyAtmosphere> It(GetWorld()); It; ++It) Hide(It->GetComponent());
    for (auto It = AuthoredVisibility.CreateIterator(); It; ++It) if (!It.Key().IsValid()) It.RemoveCurrent();
}
void UWarZoneLightingSubsystem::RestoreAuthoredEnvironment()
{
    for (const auto& Entry : AuthoredVisibility) if (Entry.Key.IsValid()) Entry.Key->SetVisibility(Entry.Value);
    AuthoredVisibility.Empty();
}
bool UWarZoneLightingSubsystem::Apply(FName Zone, FVector Origin)
{
    const auto* Profile = FindProfile(Zone);
    if (!Profile || Origin.ContainsNaN() || GetWorld()->GetNetMode() == NM_DedicatedServer) return false;
    if (!CreateEnvironment()) return false;
    const bool bEnabled = !Profile->bAuthoredCapital;
    Sun->GetLightComponent()->SetVisibility(bEnabled); Fill->GetLightComponent()->SetVisibility(bEnabled);
    Fog->GetComponent()->SetVisibility(bEnabled); Sky->GetComponent()->SetVisibility(bEnabled); Grade->bEnabled = bEnabled;
    Ambient->GetLightComponent()->SetVisibility(bEnabled);
    if (bEnabled)
    {
        HideAuthoredEnvironment();
        Sun->SetActorRotation(Profile->SunRotation);
        Fill->SetActorRotation(FRotator(-55, Profile->SunRotation.Yaw + 180, 0));
        Sun->GetLightComponent()->SetIntensity(Profile->SunLux); Sun->GetLightComponent()->SetLightColor(Profile->SunColor);
        Fill->GetLightComponent()->SetIntensity(Profile->FillLux); Fill->GetLightComponent()->SetLightColor(Profile->FillColor);
        Ambient->SetActorLocation(Origin + FVector(0,0,500));
        Ambient->GetLightComponent()->SetIntensity(FMath::Clamp(Profile->FillLux / 8000.f, .6f, 1.5f));
        Ambient->GetLightComponent()->SetLightColor(Profile->FillColor);
        Fog->SetActorLocation(Origin); Fog->GetComponent()->SetFogDensity(Profile->FogDensity);
        Fog->GetComponent()->SetFogInscatteringColor(Profile->FogColor); Fog->GetComponent()->SetStartDistance(Profile->FogStartCm);
        auto& S = Grade->Settings;
        S.bOverride_AutoExposureMethod = true; S.AutoExposureMethod = AEM_Manual;
        S.bOverride_AutoExposureApplyPhysicalCameraExposure = true; S.AutoExposureApplyPhysicalCameraExposure = true;
        S.bOverride_CameraISO = true; S.CameraISO = 100;
        S.bOverride_CameraShutterSpeed = true; S.CameraShutterSpeed = 60;
        S.bOverride_DepthOfFieldFstop = true; S.DepthOfFieldFstop = 4;
        S.bOverride_AutoExposureBias = true; S.AutoExposureBias = Profile->ExposureBias;
        S.bOverride_ColorSaturation = true; S.ColorSaturation = FVector4(Profile->Saturation, Profile->Saturation, Profile->Saturation, 1);
        S.bOverride_ColorGammaShadows = true; S.ColorGammaShadows = FVector4(Profile->ShadowGamma, Profile->ShadowGamma, Profile->ShadowGamma, 1);
    }
    else RestoreAuthoredEnvironment();
    ActiveZone = Zone; bEnvironmentDirty = false; return true;
}
bool UWarZoneLightingSubsystem::PreviewZone(FName Zone, FVector Origin)
{
    if (GetWorld()->WorldType != EWorldType::Editor && GetWorld()->WorldType != EWorldType::EditorPreview) return false;
    return Apply(Zone, Origin);
}
bool UWarZoneLightingSubsystem::PreviewWorld(UWorld* World, FName Zone, FVector Origin)
{
    auto* Lighting = World ? World->GetSubsystem<UWarZoneLightingSubsystem>() : nullptr;
    return Lighting && Lighting->PreviewZone(Zone, Origin);
}
void UWarZoneLightingSubsystem::Deinitialize()
{
    FWorldDelegates::LevelAddedToWorld.Remove(AddedHandle); FWorldDelegates::LevelRemovedFromWorld.Remove(RemovedHandle);
    RestoreAuthoredEnvironment();
    for (AActor* Actor : TArray<AActor*>{Sun.Get(), Fill.Get(), Fog.Get(), Sky.Get(), Ambient.Get(), GradeActor.Get()})
        if (IsValid(Actor)) Actor->Destroy();
    Sun = nullptr; Fill = nullptr; Fog = nullptr; Sky = nullptr; Ambient = nullptr; Grade = nullptr; GradeActor = nullptr;
    Super::Deinitialize();
}
