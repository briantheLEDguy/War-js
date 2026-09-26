#include "WarFrontendPresentation.h"
#include "WarCharacterVisualDefinition.h"
#include "WarContentSubsystem.h"
#include "WarRuntimeSettings.h"
#include "Animation/AnimSequence.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "PreviewScene.h"
#include "RenderingThread.h"
#include "UObject/StrongObjectPtr.h"

namespace
{
    UTextureRenderTarget2D* Target(UObject* Owner, int32 Width, int32 Height, bool bHdr)
    {
        auto* Result = NewObject<UTextureRenderTarget2D>(Owner);
        Result->ClearColor = FLinearColor(0, 0, 0, 1);
        Result->InitCustomFormat(Width, Height, bHdr ? PF_FloatRGBA : PF_B8G8R8A8, bHdr);
        Result->UpdateResourceImmediate(true);
        return Result;
    }
    void Cancel(TSharedPtr<FStreamableHandle>& Handle)
    {
        if (Handle) Handle->CancelHandle();
        Handle.Reset();
    }
    void AddPath(TArray<FSoftObjectPath>& Paths, const FSoftObjectPath& Path)
    { if (Path.IsValid()) Paths.AddUnique(Path); }
}

struct FWarFrontendScene
{
    FPreviewScene Scene;
    USceneCaptureComponent2D* Capture = nullptr;
    USkeletalMeshComponent* Body = nullptr;
    FVector CharacterCenter = FVector::ZeroVector;
    float CharacterDistance = 400;
    int32 BuildIndex = 0;
    int32 PoseFrames = 0;
    bool bReady = false;
    bool bFailed = false;

    FWarFrontendScene(UTextureRenderTarget2D* RenderTarget, bool bCharacter)
        : Scene(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false)
            .SetTransactional(false).SetForceMipsResident(false).AllowAudioPlayback(false))
    {
        Capture = NewObject<USceneCaptureComponent2D>();
        Capture->TextureTarget = RenderTarget;
        Capture->CaptureSource = bCharacter ? SCS_SceneColorHDR : SCS_FinalColorLDR;
        Capture->bCaptureEveryFrame = false;
        Capture->bCaptureOnMovement = false;
        Capture->bAlwaysPersistRenderingState = true;
        Capture->PostProcessSettings.bOverride_AutoExposureMethod = true;
        Capture->PostProcessSettings.AutoExposureMethod = AEM_Manual;
        Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
        Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure = false;
        Capture->PostProcessSettings.bOverride_MotionBlurAmount = true;
        Capture->PostProcessSettings.MotionBlurAmount = 0;
        Capture->ShowFlags.SetMotionBlur(false);
        Scene.AddComponent(Capture, FTransform::Identity);
        if (!bCharacter)
        {
            Scene.DirectionalLight->SetAtmosphereSunLight(true);
            Scene.AddComponent(NewObject<USkyAtmosphereComponent>(), FTransform::Identity);
        }
    }

    void Configure(const FWarFrontendCity& City)
    {
        Scene.SetLightDirection(City.SunDirection);
        Scene.SetLightColor(City.SunColor.ToFColor(false));
        Scene.SetLightBrightness(City.SunIntensity);
        Scene.SetSkyBrightness(City.SkyIntensity);
        auto* Fog = NewObject<UExponentialHeightFogComponent>();
        Fog->SetFogDensity(.008f);
        Fog->SetFogInscatteringColor(City.FogColor);
        Scene.AddComponent(Fog, FTransform(FVector(0, 0, -800)));
    }

    bool Build(const FWarFrontendCity& City, FString& Error)
    {
        // Amortize registration across frames; instances share geometry and material state.
        const int32 End = FMath::Min(BuildIndex + 24, City.Placements.Num());
        for (; BuildIndex < End; ++BuildIndex)
        {
            const auto& Row = City.Placements[BuildIndex];
            if (!Row.Mesh.Get()) { bFailed = true; Error = TEXT("City mesh unavailable. Restore frontend content and retry."); return false; }
            auto* Mesh = NewObject<UInstancedStaticMeshComponent>();
            Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Mesh->SetCanEverAffectNavigation(false);
            Mesh->SetStaticMesh(Row.Mesh.Get());
            for (int32 Index = 0; Index < Row.Materials.Num(); ++Index)
            {
                if (!Row.Materials[Index].Get()) { bFailed = true; Error = TEXT("City material unavailable. Restore frontend content and retry."); return false; }
                Mesh->SetMaterial(Index, Row.Materials[Index].Get());
            }
            Scene.AddComponent(Mesh, FTransform::Identity);
            Mesh->AddInstances(Row.Instances, false, false, false);
        }
        bReady = BuildIndex == City.Placements.Num();
        return true;
    }

    void SetShot(const FWarFrontendShot& Shot, float Progress)
    {
        const FVector Eye = FMath::Lerp(Shot.Eye, Shot.EndEye, FMath::SmoothStep(0.f, 1.f, Progress));
        Capture->SetWorldLocationAndRotation(Eye, (Shot.Target - Eye).Rotation());
        Capture->FOVAngle = Shot.FieldOfView;
    }

    void SetCharacterView(float Yaw)
    {
        const FVector Offset = FRotator(0, Yaw, 0).RotateVector(FVector(CharacterDistance, 0, 15));
        Capture->SetWorldLocationAndRotation(CharacterCenter + Offset, (-Offset).Rotation());
        Capture->FOVAngle = 34;
    }

    float FrameCharacter()
    {
        Body->UpdateBounds();
        FBox Bounds = Body->Bounds.GetBox();
        for (int32 Bone = 0; Bone < Body->GetNumBones(); ++Bone) Bounds += Body->GetBoneLocation(Body->GetBoneName(Bone));
        TArray<USceneComponent*> Children; Body->GetChildrenComponents(true, Children);
        for (auto* Child : Children) if (auto* Primitive = Cast<UPrimitiveComponent>(Child))
        { Primitive->UpdateComponentToWorld(); Primitive->UpdateBounds(); Bounds += Primitive->Bounds.GetBox(); }
        CharacterCenter = Bounds.GetCenter();
        const FVector Extent = Bounds.GetExtent();
        // A cylinder encloses every yaw, with space for idle movement and equipment.
        CharacterDistance = FMath::Max(Extent.Z * .8f, FVector2D(Extent.X, Extent.Y).Size())
            / FMath::Tan(FMath::DegreesToRadians(17.f)) * 1.15f;
        FVector Forward = FVector::ZeroVector;
        for (const TCHAR* Side : {TEXT("L"), TEXT("R")})
        {
            const FName Toe(*FString::Printf(TEXT("toe_%s"), Side)), Foot(*FString::Printf(TEXT("foot_%s"), Side));
            if (Body->DoesSocketExist(Toe) && Body->DoesSocketExist(Foot))
                Forward += Body->GetSocketLocation(Toe) - Body->GetSocketLocation(Foot);
        }
        Forward.Z = 0;
        return (Forward.IsNearlyZero() ? Body->GetComponentRotation().Yaw : Forward.Rotation().Yaw) - 15;
    }
};

bool UWarFrontendPresentationDefinition::Validate(FString& Error) const
{
    if (Cities.Num() != 2 || Cities[0].ZoneId != TEXT("aegis_capital") || Cities[1].ZoneId != TEXT("riftspire_capital")
        || !FMath::IsFinite(HoldSeconds) || HoldSeconds < 1 || !FMath::IsFinite(FadeSeconds) || FadeSeconds < .1f
        || CharacterComposite.IsNull())
    { Error = TEXT("Frontend presentation needs both capitals, valid timing and its character material."); return false; }
    for (const auto& City : Cities)
    {
        if (City.Placements.IsEmpty() || City.Shots.Num() != 2)
        { Error = TEXT("Each capital needs authored geometry and two camera views."); return false; }
        for (const auto& Shot : City.Shots)
            if (Shot.Eye.ContainsNaN() || Shot.EndEye.ContainsNaN() || Shot.Target.ContainsNaN()
                || Shot.Eye.Equals(Shot.Target) || Shot.EndEye.Equals(Shot.Target)
                || !FMath::IsFinite(Shot.FieldOfView) || Shot.FieldOfView < 20 || Shot.FieldOfView > 100)
            { Error = TEXT("A capital camera view is invalid."); return false; }
        for (const auto& Row : City.Placements)
        {
            if (Row.Mesh.IsNull() || Row.Instances.IsEmpty() || Row.Mesh.ToString().StartsWith(TEXT("/Engine/BasicShapes/")))
            { Error = TEXT("Frontend scenery requires authored native meshes."); return false; }
            for (const auto& Transform : Row.Instances)
                if (Transform.ContainsNaN()) { Error = TEXT("City placement contains an invalid transform."); return false; }
        }
    }
    Error.Reset(); return true;
}

void FWarFrontendCycle::Advance(float Delta, bool bReady, bool bReduced, float Hold, float Fade)
{
    if (!bReady || bReduced || !FMath::IsFinite(Delta) || Delta <= 0) return;
    const double Duration = FMath::Max(.1f, Hold + Fade);
    Time += FMath::Min(Delta, .1f);
    if (Time >= Duration) { Time -= Duration; Shot = (Shot + 1) % 4; }
}
float FWarFrontendCycle::Blend(float Hold, float Fade) const
{ return FMath::SmoothStep(0.f, 1.f, FMath::Clamp(float((Time - Hold) / FMath::Max(.1f, Fade)), 0.f, 1.f)); }
float FWarFrontendCycle::Progress(float Hold, float Fade) const
{ return FMath::Clamp(float(Time / FMath::Max(.1f, Hold + Fade)), 0.f, 1.f); }

UWarFrontendPresentation::UWarFrontendPresentation() = default;
UWarFrontendPresentation::~UWarFrontendPresentation() = default;

void UWarFrontendPresentation::Initialize()
{
    if (bRunning || IsRunningDedicatedServer() || !FApp::CanEverRender()) return;
    bRunning = true;
    CityError = TEXT("Preparing capital views...");
    const auto Path = GetDefault<UWarRuntimeSettings>()->FrontendPresentation.ToSoftObjectPath();
    DefinitionLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,
        FStreamableDelegate::CreateWeakLambda(this, [this, Path]() {
            if (!bRunning) return;
            Definition = Cast<UWarFrontendPresentationDefinition>(Path.ResolveObject());
            if (!Definition) { CityError = TEXT("Capital presentation is not installed. Restore frontend content and retry."); return; }
            if (!Definition->Validate(CityError)) return;
            LoadCities();
        }));
}

void UWarFrontendPresentation::LoadCities()
{
    TArray<FSoftObjectPath> Paths;
    AddPath(Paths, Definition->CharacterComposite.ToSoftObjectPath());
    for (const auto& City : Definition->Cities)
        for (const auto& Row : City.Placements)
        {
            AddPath(Paths, Row.Mesh.ToSoftObjectPath());
            for (const auto& Material : Row.Materials) AddPath(Paths, Material.ToSoftObjectPath());
        }
    CityError = TEXT("Loading capital views...");
    CityLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this, [this]() {
            if (!bRunning) return;
            CityTargets.SetNum(2);
            for (int32 Index = 0; Index < 2; ++Index)
            {
                CityTargets[Index] = Target(this, 1600, 900, false);
                Cities[Index] = MakeShared<FWarFrontendScene>(CityTargets[Index], false);
                Cities[Index]->Configure(Definition->Cities[Index]);
            }
            if (auto* Material = Definition->CharacterComposite.Get())
            {
                CharacterTarget = Target(this, 800, 1000, true);
                CharacterMaterial = UMaterialInstanceDynamic::Create(Material, this);
                CharacterMaterial->SetTextureParameterValue(TEXT("CharacterTexture"), CharacterTarget);
                if (!SelectedRace.IsNone()) SelectCharacter(SelectedRace, SelectedCareer, SelectedBody);
            }
            else CharacterStatus = TEXT("Character presentation material unavailable. Restore content and retry.");
            CityError.Reset(); bDirty = true;
        }));
}

void UWarFrontendPresentation::Shutdown()
{
    bRunning = false; ++SelectionGeneration;
    Cancel(DefinitionLoad); Cancel(CityLoad); Cancel(CharacterLoad);
    CharacterScene.Reset(); Cities[0].Reset(); Cities[1].Reset();
    CharacterMaterial = nullptr; CharacterTarget = nullptr; CityTargets.Reset();
    SelectedVisual = nullptr; Definition = nullptr;
    RetainedCityTarget = nullptr; RetainedCityLabel.Reset(); DisplayCity = 0;
    Cycle = {}; CaptureTime = 0; bDirty = true;
}
void UWarFrontendPresentation::BeginDestroy() { Shutdown(); Super::BeginDestroy(); }
void UWarFrontendPresentation::Retry()
{
    // Keep the last rendered capital visible while replacement content is loading.
    TStrongObjectPtr<UTextureRenderTarget2D> Previous(GetCityTarget(GetActiveCity()));
    const FString Label = GetCityLabel();
    Shutdown(); RetainedCityTarget = Previous.Get(); RetainedCityLabel = Label; Initialize();
}

void UWarFrontendPresentation::SelectCharacter(FName Race, FName Career, FName Body)
{
    SelectedRace = Race; SelectedCareer = Career; SelectedBody = Body;
    const uint64 Generation = ++SelectionGeneration;
    Cancel(CharacterLoad); CharacterScene.Reset(); SelectedVisual = nullptr;
    CharacterStatus = TEXT("Loading character..."); bDirty = true;
    if (!bRunning || !CharacterMaterial) return;
    TArray<FSoftObjectPath> Paths;
    for (const auto& Row : GetDefault<UWarRuntimeSettings>()->PlayableRoster) AddPath(Paths, Row.ToSoftObjectPath());
    CharacterLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this, [this, Generation, Race, Career, Body]() {
            if (!bRunning || Generation != SelectionGeneration) return;
            UWarCharacterVisualDefinition* Visual = nullptr;
            for (const auto& Row : GetDefault<UWarRuntimeSettings>()->PlayableRoster)
                if (auto* Candidate = Row.Get())
                    if (Candidate->RaceId == Race && Candidate->ClassId == Career && Candidate->BodyVariant == Body)
                    { Visual = Candidate; break; }
            if (!Visual) { CharacterStatus = TEXT("This character model is not installed. Choose another character or retry."); return; }
            SelectedVisual = Visual;
            TArray<FSoftObjectPath> Assets;
            AddPath(Assets, Visual->SkeletalMesh.ToSoftObjectPath());
            AddPath(Assets, Visual->IdleAnimation.ToSoftObjectPath());
            AddPath(Assets, Visual->WeaponMesh.ToSoftObjectPath());
            AddPath(Assets, Visual->ShieldMesh.ToSoftObjectPath());
            for (const auto& Animation : Visual->ImportedAnimations) AddPath(Assets, Animation.Value.ToSoftObjectPath());
            AddPath(Assets, Visual->AnimationBlueprint.ToSoftObjectPath());
            CharacterLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(Assets,
                FStreamableDelegate::CreateWeakLambda(this, [this, Generation, Visual]() { FinishCharacter(Generation, Visual); }));
        }));
}

void UWarFrontendPresentation::FinishCharacter(uint64 Generation, UWarCharacterVisualDefinition* Visual)
{
    if (!bRunning || Generation != SelectionGeneration) return;
    auto* Instance = GetTypedOuter<UGameInstance>();
    auto* Content = Instance ? Instance->GetSubsystem<UWarContentSubsystem>() : nullptr;
    FString Error;
    if (!Content || !Visual->ValidateForSpawn(Visual->Realm, Error) || !Content->ValidatePlayableVisual(Visual, Error))
    { CharacterStatus = Error.IsEmpty() ? TEXT("Character content is not ready. Restore content and retry.") : Error; return; }
    if (!Visual->IdleAnimation.Get()) { CharacterStatus = TEXT("This character has no approved preview idle. Restore content and retry."); return; }
    CharacterScene = MakeShared<FWarFrontendScene>(CharacterTarget, true);
    auto& Preview = *CharacterScene;
    Preview.Scene.SetLightDirection(FRotator(-25, 160, 0));
    Preview.Scene.SetLightBrightness(7);
    Preview.Scene.SetSkyBrightness(1.4f);
    auto* Fill = NewObject<UDirectionalLightComponent>();
    Fill->SetIntensity(2.5f);
    Fill->SetLightColor(FLinearColor(.62f, .76f, 1.f));
    Fill->SetCastShadows(false);
    Preview.Scene.AddComponent(Fill, FTransform(FRotator(-20, -25, 0)));
    auto* Body = NewObject<USkeletalMeshComponent>();
    Preview.Body = Body;
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->SetSkeletalMesh(Visual->SkeletalMesh.Get());
    Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Preview.Scene.AddComponent(Body, Visual->MeshTransform);
    Body->PlayAnimation(Visual->IdleAnimation.Get(), true);
    Body->TickAnimation(0, false); Body->RefreshBoneTransforms();
    const bool bStored = Visual->AnimationStyle == TEXT("spell");
    const auto Equip = [&](UStaticMesh* Mesh, FName Hand, const FTransform& Grip, const FTransform& Stored) {
        if (!Mesh) return;
        auto* Part = NewObject<UStaticMeshComponent>();
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetStaticMesh(Mesh);
        Preview.Scene.AddComponent(Part, FTransform::Identity);
        Part->AttachToComponent(Body, FAttachmentTransformRules::KeepRelativeTransform, bStored ? FName(TEXT("upper_chest")) : Hand);
        Part->SetRelativeTransform(bStored ? Stored : Grip);
    };
    Equip(Visual->WeaponMesh.Get(), TEXT("hand_R"), Visual->WeaponGrip, Visual->WeaponStowed);
    Equip(Visual->ShieldMesh.Get(), TEXT("hand_L"), Visual->ShieldGrip, Visual->ShieldStowed);
    // Registration evaluates a reference pose in this frame. Frame the equipped idle
    // on subsequent frames so each rig faces the camera and stowed weapons fit.
    bDirty = true;
}

void UWarFrontendPresentation::Tick(float Delta, bool bVisible)
{
    if (!bRunning || !bVisible || !Definition) return;
    for (int32 Index = 0; Index < 2; ++Index)
    {
        if (Cities[Index] && !Cities[Index]->bReady && !Cities[Index]->bFailed)
            Cities[Index]->Build(Definition->Cities[Index], CityError);
    }
    const bool ReadyA = Cities[0] && Cities[0]->bReady, ReadyB = Cities[1] && Cities[1]->bReady;
    if (!ReadyA && !ReadyB) return;
    Cycle.Advance(Delta, ReadyA && ReadyB, bReducedMotion, Definition->HoldSeconds, Definition->FadeSeconds);
    DisplayCity = ReadyA && ReadyB ? Cycle.Shot % 2 : ReadyA ? 0 : 1;
    CaptureTime = FMath::Min(.1f, CaptureTime + FMath::Clamp(Delta, 0.f, .1f));
    if (!bDirty && (CaptureTime < 1.f / 30.f || bReducedMotion)) return;
    const float Step = CaptureTime; CaptureTime = 0;
    const int32 Active = GetActiveCity(), Incoming = 1 - Active;
    const int32 Shot = Cycle.Shot / 2;
    Cities[Active]->SetShot(Definition->Cities[Active].Shots[Shot], Cycle.Progress(Definition->HoldSeconds, Definition->FadeSeconds));
    Cities[Active]->Scene.GetWorld()->Tick(LEVELTICK_ViewportsOnly, Step);
    Cities[Active]->Capture->CaptureScene();
    if (ReadyA && ReadyB && (GetBlend() > 0 || bDirty))
    {
        const int32 NextShot = ((Cycle.Shot + 1) % 4) / 2;
        Cities[Incoming]->SetShot(Definition->Cities[Incoming].Shots[NextShot], 0);
        Cities[Incoming]->Scene.GetWorld()->Tick(LEVELTICK_ViewportsOnly, Step);
        Cities[Incoming]->Capture->CaptureScene();
    }
    RetainedCityTarget = nullptr; RetainedCityLabel.Reset();
    if (CharacterScene && CharacterScene->Body)
    {
        auto& Preview = *CharacterScene;
        Preview.Body->TickAnimation(bReducedMotion ? 0 : Step, false);
        Preview.Body->RefreshBoneTransforms();
        if (!Preview.bReady && ++Preview.PoseFrames >= 2)
        {
            DefaultCharacterYaw = Preview.FrameCharacter();
            ResetRotation(); Preview.bReady = true; CharacterStatus.Reset();
        }
        Preview.SetCharacterView(CharacterYaw);
        Preview.Capture->CaptureScene();
    }
    bDirty = CharacterScene && !CharacterScene->bReady;
}

void UWarFrontendPresentation::Rotate(float Degrees) { CharacterYaw = FMath::UnwindDegrees(CharacterYaw + Degrees); bDirty = true; }
void UWarFrontendPresentation::ResetRotation() { CharacterYaw = DefaultCharacterYaw; bDirty = true; }
void UWarFrontendPresentation::SetReducedMotion(bool bValue) { bReducedMotion = bValue; bDirty = true; }
float UWarFrontendPresentation::GetBlend() const
{ return Definition && Cities[0] && Cities[1] && Cities[0]->bReady && Cities[1]->bReady ? Cycle.Blend(Definition->HoldSeconds, Definition->FadeSeconds) : 0; }
FString UWarFrontendPresentation::GetCityLabel() const
{ return RetainedCityTarget ? RetainedCityLabel : Definition && Definition->Cities.IsValidIndex(GetActiveCity()) ? Definition->Cities[GetActiveCity()].Label : FString(); }
UTextureRenderTarget2D* UWarFrontendPresentation::GetCityTarget(int32 Index) const
{
    if (Index < 0 || Index > 1) return nullptr;
    if (Cities[Index] && Cities[Index]->bReady && CityTargets.IsValidIndex(Index)) return CityTargets[Index].Get();
    return Index == DisplayCity ? RetainedCityTarget.Get() : nullptr;
}
bool UWarFrontendPresentation::HasCharacter() const { return CharacterScene && CharacterScene->bReady; }
