#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SceneCapture2D.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextureCube.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "EngineUtils.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#endif

/** Optional rendered evidence from the same actors/events exercised by automation. */
class FWarAnimationGameplayCapture
{
public:
    explicit FWarAnimationGameplayCapture(UWorld* InWorld):World(InWorld)
    {
        if (!FParse::Param(FCommandLine::Get(),TEXT("WarCaptureSuppliedAnimation"))) return;
        auto* Floor=World->SpawnActor<AStaticMeshActor>(FVector(0,0,-1),FRotator::ZeroRotator);
        Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
        Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane")));
        Floor->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Floor->SetActorScale3D(FVector(100,100,1));
        for (const FRotator Direction:{FRotator(-35,-90,0),FRotator(-25,40,0),FRotator(-20,180,0)})
        {
            auto* Light=World->SpawnActor<ADirectionalLight>(FVector(0,0,400),Direction);
            Light->GetLightComponent()->SetMobility(EComponentMobility::Movable);
            Light->GetLightComponent()->SetIntensity(10000);
        }
        auto* Sky=World->SpawnActor<ASkyLight>();
        Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
        Sky->GetLightComponent()->SourceType=SLS_SpecifiedCubemap;
        Sky->GetLightComponent()->SetCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Engine/MapTemplates/Sky/DaylightAmbientCubemap")));
        Sky->GetLightComponent()->SetIntensity(.8f);
        Capture=World->SpawnActor<ASceneCapture2D>();
        auto* Camera=Capture->GetCaptureComponent2D();
        Camera->TextureTarget=UKismetRenderingLibrary::CreateRenderTarget2D(World,720,860,RTF_RGBA8);
        Camera->CaptureSource=SCS_FinalColorLDR; Camera->bCaptureEveryFrame=false; Camera->bCaptureOnMovement=false;
        Camera->bAlwaysPersistRenderingState=true; Camera->FOVAngle=42; Camera->PostProcessBlendWeight=1;
        auto& Settings=Camera->PostProcessSettings;
        Settings.bOverride_AutoExposureMethod=true; Settings.AutoExposureMethod=AEM_Manual;
        Settings.bOverride_AutoExposureBias=true; Settings.AutoExposureBias=1.5f;
        Settings.bOverride_AutoExposureApplyPhysicalCameraExposure=true; Settings.AutoExposureApplyPhysicalCameraExposure=true;
        Directory=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("AnimationGameplayCapture"));
        IFileManager::Get().MakeDirectory(*Directory,true);
    }
    bool Enabled() const { return Capture!=nullptr; }
    void Frame(AWarCharacter* Pawn,const FString& Label)
    {
        if (!Capture) return;
#if WITH_EDITOR
        // Assets loaded by a synchronous automation tick can still have pending
        // render data/shaders; wait before judging equipment or materials.
        FAssetCompilingManager::Get().FinishAllCompilation();
        if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
#endif
        auto* Camera=Capture->GetCaptureComponent2D();
        Camera->HiddenActors.Reset();
        for (TActorIterator<AWarCharacter> Other(World);Other;++Other)
            if (*Other!=Pawn) Camera->HiddenActors.Add(*Other);
        FBox Bounds=Pawn->GetMesh()->Bounds.GetBox();
        TInlineComponentArray<UStaticMeshComponent*> Equipment(Pawn);
        for (const auto* Part:Equipment) if (Part->GetStaticMesh()
            && (Part->GetFName()==TEXT("EquippedWeapon") || Part->GetFName()==TEXT("EquippedShield"))) Bounds+=Part->Bounds.GetBox();
        const FVector Center=Bounds.GetCenter();
        const double Distance=FMath::Max(600.,Bounds.GetExtent().GetMax()*4.);
        int32 View=0;
        for (const FVector Offset:{FVector(1,.35,.12),FVector(-.3,1,.12)})
        {
            const FVector Location=Center+Offset.GetSafeNormal()*Distance;
            Capture->SetActorLocationAndRotation(Location,(Center-Location).Rotation());
            World->SendAllEndOfFrameUpdates();
            for (int32 Warmup=0;Warmup<3;++Warmup) Capture->GetCaptureComponent2D()->CaptureScene();
            const FString File=Pawn->GetAnimationProfile().ToString()+TEXT("_")+Label+FString::Printf(TEXT("_%d.png"),View++);
            UKismetRenderingLibrary::ExportRenderTarget(World,Capture->GetCaptureComponent2D()->TextureTarget,Directory,File);
            auto Row=MakeShared<FJsonObject>(); Row->SetStringField(TEXT("file"),File);
            Row->SetStringField(TEXT("profile"),Pawn->GetAnimationProfile().ToString());
            Row->SetStringField(TEXT("role"),Pawn->GetPlayingAnimation().ToString());
            Row->SetNumberField(TEXT("worldTime"),World->GetTimeSeconds());
            Row->SetNumberField(TEXT("actionStart"),Pawn->GetReplicatedMotion().Start);
            Frames.Add(MakeShared<FJsonValueObject>(Row));
        }
    }
    void Save(bool bPassed)
    {
        if (!Capture) return;
        auto Report=MakeShared<FJsonObject>(); Report->SetArrayField(TEXT("frames"),Frames);
        Report->SetBoolField(TEXT("gameplayPassed"),bPassed);
        Report->SetStringField(TEXT("method"),TEXT("Production character, ability runtime, world ticks and equipment; captured during native gameplay automation"));
        FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*FPaths::Combine(Directory,TEXT("frames.json")));
    }
private:
    UWorld* World;
    ASceneCapture2D* Capture=nullptr;
    FString Directory;
    TArray<TSharedPtr<FJsonValue>> Frames;
};
#endif
