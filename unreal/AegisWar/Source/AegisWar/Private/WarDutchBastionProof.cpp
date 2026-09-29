#include "WarDutchBastionProof.h"
#include "WarCharacter.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMemory.h"
#include "UnrealClient.h"
#include "RHIStats.h"
#include "ContentStreaming.h"
#include "HAL/IConsoleManager.h"

namespace
{
    FVector Point(const TArray<TSharedPtr<FJsonValue>>& Values)
    {
        return Values.Num()==3 ? FVector(Values[0]->AsNumber(),Values[1]->AsNumber(),Values[2]->AsNumber()) : FVector::ZeroVector;
    }
}

bool UWarDutchBastionProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(),TEXT("WarDutchBastionProof"))
        && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentGM"));
#endif
}
bool UWarDutchBastionProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type==EWorldType::Game; }
TStatId UWarDutchBastionProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarDutchBastionProof,STATGROUP_Tickables); }

void UWarDutchBastionProof::Finish(bool Passed,const FString& Detail)
{
    bFinished=true;
    auto Report=MakeShared<FJsonObject>();
    Report->SetBoolField(TEXT("passed"),Passed);Report->SetStringField(TEXT("detail"),Detail);
    Report->SetStringField(TEXT("signature"),Signature);Report->SetStringField(TEXT("map"),GetWorld()->GetOutermost()->GetName());
    Report->SetNumberField(TEXT("views"),ViewIndex);Report->SetNumberField(TEXT("routesWalked"),RouteIndex);
    Report->SetArrayField(TEXT("routeFailures"),RouteFailures);
    Report->SetArrayField(TEXT("viewPerformance"),ViewPerformance);
    Report->SetBoolField(TEXT("visualApproved"),false);Report->SetBoolField(TEXT("citywideAcceptance"),false);
    Report->SetBoolField(TEXT("releaseAcceptance"),false);
    if (auto* PC=GetWorld()->GetFirstPlayerController())
        if (auto* Pawn=Cast<AWarCharacter>(PC->GetPawn()))
        {
            Report->SetNumberField(TEXT("capsuleRadiusCm"),Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius());
            Report->SetNumberField(TEXT("capsuleHeightCm"),Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()*2);
        }
    Frames.Sort();Report->SetNumberField(TEXT("frameSamples"),Frames.Num());
    if (!Frames.IsEmpty()) Report->SetNumberField(TEXT("p95FrameMs"),Frames[FMath::Min(Frames.Num()-1,FMath::FloorToInt(Frames.Num()*.95))]);
    DrawCalls.Sort();Primitives.Sort();
    if (!DrawCalls.IsEmpty()) Report->SetNumberField(TEXT("p95DrawCalls"),DrawCalls[FMath::Min(DrawCalls.Num()-1,FMath::FloorToInt(DrawCalls.Num()*.95))]);
    if (!Primitives.IsEmpty()) Report->SetNumberField(TEXT("p95Primitives"),Primitives[FMath::Min(Primitives.Num()-1,FMath::FloorToInt(Primitives.Num()*.95))]);
    Report->SetNumberField(TEXT("peakStreamingRequestsAfterSettle"),PeakStreamingRequests);
    Report->SetNumberField(TEXT("usedPhysicalMiB"),FPlatformMemory::GetStats().UsedPhysical/1048576.0);
    if (auto* Limit=IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"))) Report->SetNumberField(TEXT("frameLimit"),Limit->GetFloat());
    if (auto* VSync=IConsoleManager::Get().FindConsoleVariable(TEXT("r.VSync"))) Report->SetNumberField(TEXT("vSync"),VSync->GetInt());
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(Directory/TEXT("report.json")));
    UE_LOG(LogTemp,Display,TEXT("WAR_DUTCH_PROOF=%s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),*Detail);
    FPlatformMisc::RequestExitWithStatus(false,Passed?0:1);
}

void UWarDutchBastionProof::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds();if (Started<0) Started=Now;
    if (!bInitialized)
    {
        FString Text;TSharedPtr<FJsonObject> Config;
        Directory=FPaths::ProjectSavedDir()/TEXT("DutchBastion");IFileManager::Get().MakeDirectory(*Directory,true);
        if (!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Migration/dutch-bastion-proof.json")))
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config) || !Config.IsValid())
        { Finish(false,TEXT("Missing architecture proof configuration"));return; }
        const FString Map=GetWorld()->GetOutermost()->GetName();
        if (!Map.StartsWith(TEXT("/Game/WorldRebuild/DutchBastion_")) || Map!=Config->GetStringField(TEXT("map")))
        { Finish(false,TEXT("Proof requires its exact isolated revision"));return; }
        Signature=Config->GetStringField(TEXT("signature"));
        if (Config->TryGetNumberField(TEXT("viewSettleSeconds"),ViewSettleSeconds)) ViewSettleSeconds=FMath::Clamp(ViewSettleSeconds,3.0,30.0);
        Views=Config->GetArrayField(TEXT("views"));Routes=Config->GetArrayField(TEXT("routes"));
        bInitialized=true;
    }
    auto* PC=GetWorld()->GetFirstPlayerController();auto* Pawn=PC?Cast<AWarCharacter>(PC->GetPawn()):nullptr;
    if (!Pawn || !Pawn->IsVisualReady())
    { if (Now-Started>60) Finish(false,TEXT("Playable character unavailable"));return; }
    if (ViewIndex<Views.Num())
    {
        auto View=Views[ViewIndex]->AsObject();
        if (!bPositioned)
        {
            const FVector Eye=Point(View->GetArrayField(TEXT("eye"))),Target=Point(View->GetArrayField(TEXT("target")));
            if (!Camera.IsValid()) Camera=GetWorld()->SpawnActor<ACameraActor>();
            Camera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());Camera->GetCameraComponent()->SetFieldOfView(68);
            PC->bAutoManageActiveCameraTarget=false;PC->SetViewTarget(Camera.Get());
            Next=Now+ViewSettleSeconds;bPositioned=true;bCaptured=false;return;
        }
        if (Now>Next-3 && DeltaTime>0)
        {
            Frames.Add(DeltaTime*1000);
            ViewFrames.Add(DeltaTime*1000);ViewDrawCalls.Add(GNumDrawCallsRHI[0]);
            DrawCalls.Add(GNumDrawCallsRHI[0]);Primitives.Add(GNumPrimitivesDrawnRHI[0]);
            PeakStreamingRequests=FMath::Max(PeakStreamingRequests,IStreamingManager::Get().GetNumWantingResources());
        }
        if (Now<Next) return;
        if (!bCaptured)
        {
            FScreenshotRequest::RequestScreenshot(Directory/FString::Printf(TEXT("view_%02d.png"),ViewIndex),false,false);
            bCaptured=true;Next=Now+1;return;
        }
        ViewFrames.Sort();ViewDrawCalls.Sort();
        auto Metric=MakeShared<FJsonObject>();Metric->SetStringField(TEXT("id"),View->GetStringField(TEXT("id")));
        if (!ViewFrames.IsEmpty()) Metric->SetNumberField(TEXT("p95FrameMs"),ViewFrames[FMath::Min(ViewFrames.Num()-1,FMath::FloorToInt(ViewFrames.Num()*.95))]);
        if (!ViewDrawCalls.IsEmpty()) Metric->SetNumberField(TEXT("p95DrawCalls"),ViewDrawCalls[FMath::Min(ViewDrawCalls.Num()-1,FMath::FloorToInt(ViewDrawCalls.Num()*.95))]);
        Metric->SetNumberField(TEXT("physicalMiB"),FPlatformMemory::GetStats().UsedPhysical/1048576.0);
        ViewPerformance.Add(MakeShared<FJsonValueObject>(Metric));ViewFrames.Reset();ViewDrawCalls.Reset();
        UE_LOG(LogTemp,Display,TEXT("WAR_DUTCH_VIEW=%d/%d"),ViewIndex+1,Views.Num());
        ++ViewIndex;bPositioned=false;return;
    }
    if (RouteIndex>=Routes.Num()) { Finish(RouteFailures.IsEmpty(),TEXT("Saved lighting views and configured capsule routes completed; inspect routeFailures"));return; }
    auto Route=Routes[RouteIndex]->AsObject();const auto Points=Route->GetArrayField(TEXT("points"));
    if (Points.Num()<2) { Finish(false,TEXT("Missing traversal route"));return; }
    if (!bPositioned)
    {
        Pawn->SetActorLocation(Point(Points[0]->AsArray())+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3),false);
        Pawn->GetCharacterMovement()->StopMovementImmediately();Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        RouteStarted=Now;LastProgress=Now;BestDistance=MAX_dbl;Waypoint=1;Next=Now+.5;bPositioned=true;return;
    }
    if (Now<Next) return;
    FVector Feet=Pawn->GetActorLocation()-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector Target=Point(Points[Waypoint]->AsArray());
    const double Distance=FVector::Dist2D(Feet,Target);
    if (Distance<BestDistance-5) { BestDistance=Distance;LastProgress=Now; }
    if (Now-RouteStarted>75 || Now-LastProgress>10)
    {
        auto Failure=MakeShared<FJsonObject>();
        Failure->SetStringField(TEXT("id"),Route->GetStringField(TEXT("id")));
        Failure->SetNumberField(TEXT("waypoint"),Waypoint);
        Failure->SetStringField(TEXT("feet"),Feet.ToString());Failure->SetStringField(TEXT("target"),Target.ToString());
        RouteFailures.Add(MakeShared<FJsonValueObject>(Failure));
        UE_LOG(LogTemp,Warning,TEXT("WAR_DUTCH_ROUTE_BLOCKED=%s feet=%s target=%s"),*Route->GetStringField(TEXT("id")),*Feet.ToString(),*Target.ToString());
        Pawn->GetCharacterMovement()->StopMovementImmediately();++RouteIndex;bPositioned=false;return;
    }
    if (FVector::Dist2D(Feet,Target)<30 && FMath::Abs(Feet.Z-Target.Z)<45)
    {
        BestDistance=MAX_dbl;LastProgress=Now;
        if (++Waypoint>=Points.Num())
        {
            UE_LOG(LogTemp,Display,TEXT("WAR_DUTCH_ROUTE=%s %d/%d"),*Route->GetStringField(TEXT("id")),RouteIndex+1,Routes.Num());
            Pawn->GetCharacterMovement()->StopMovementImmediately();++RouteIndex;bPositioned=false;
        }
        return;
    }
    Pawn->AddMovementInput((Target-Feet).GetSafeNormal2D(),1.0f,true);
}
