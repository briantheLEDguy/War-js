#include "WarCapitalExpansionProof.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarWorldEditSubsystem.h"
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

namespace
{
    FVector ReadVector(const TArray<TSharedPtr<FJsonValue>>& Values)
    {
        return Values.Num() == 3 ? FVector(Values[0]->AsNumber(), Values[1]->AsNumber(), Values[2]->AsNumber()) : FVector::ZeroVector;
    }
}

bool UWarCapitalExpansionProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarExpansionProof"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentGM"));
#endif
}
bool UWarCapitalExpansionProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type == EWorldType::Game; }
TStatId UWarCapitalExpansionProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarCapitalExpansionProof, STATGROUP_Tickables); }

void UWarCapitalExpansionProof::Finish(bool Passed, const FString& Detail)
{
    bFinished = true;
    const auto Report = MakeShared<FJsonObject>();
    Report->SetBoolField(TEXT("passed"), Passed);
    Report->SetStringField(TEXT("detail"), Detail);
    Report->SetNumberField(TEXT("views"), ViewIndex);
    Report->SetNumberField(TEXT("interiorsWalked"), RouteIndex);
    Report->SetBoolField(TEXT("before"), bBefore);
    Report->SetBoolField(TEXT("gmEditUndoRedo"), bGmVerified);
    Report->SetBoolField(TEXT("gmDraftReloadAfterTravel"), bGmReloadVerified);
    Report->SetBoolField(TEXT("ownerDraftImportedIntoIsolatedProof"),bOwnerDraftImported);
    Report->SetBoolField(TEXT("interiorLightingFollowsGmEdit"),bLightingFollowsEdit);
    if (const auto* PC=GetWorld()->GetFirstPlayerController())
        if (const auto* Pawn=Cast<AWarCharacter>(PC->GetPawn()))
        {
            Report->SetNumberField(TEXT("capsuleRadiusCm"),Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius());
            Report->SetNumberField(TEXT("capsuleHeightCm"),Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()*2);
        }
    Frames.Sort();
    if (!Frames.IsEmpty()) Report->SetNumberField(TEXT("p95FrameMs"), Frames[FMath::Min(Frames.Num()-1, FMath::FloorToInt(Frames.Num()*.95))]);
    Report->SetNumberField(TEXT("frameSamples"), Frames.Num());
    Report->SetNumberField(TEXT("usedPhysicalMiB"), FPlatformMemory::GetStats().UsedPhysical / 1048576.0);
    Report->SetBoolField(TEXT("releaseAcceptance"), false);
    FString Json;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json, *(Directory / TEXT("report.json")));
    UE_LOG(LogTemp, Display, TEXT("WAR_EXPANSION_PROOF=%s %s"), Passed ? TEXT("PASS") : TEXT("FAIL"), *Detail);
    FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
}

void UWarCapitalExpansionProof::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Started < 0) Started = Now;
    if (!bInitialized)
    {
        FString Run;
        FParse::Value(FCommandLine::Get(), TEXT("WarExpansionRun="), Run);
        if (Run.IsEmpty() || Run.Len() > 64 || Run.Contains(TEXT("..")) || Run.Contains(TEXT("/")) || Run.Contains(TEXT("\\")))
        { bFinished = true; FPlatformMisc::RequestExitWithStatus(false, 1); return; }
        bBefore = FParse::Param(FCommandLine::Get(), TEXT("WarExpansionBefore"));
        Directory = FPaths::ProjectSavedDir() / TEXT("CapitalExpansion") / Run / (bBefore ? TEXT("before") : TEXT("after"));
        IFileManager::Get().MakeDirectory(*Directory, true);
        FString Text; TSharedPtr<FJsonObject> Config;
        if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Migration/capital-expansion-proof.json")))
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Config) || !Config.IsValid())
        { Finish(false, TEXT("Missing expansion proof configuration")); return; }
        Views = Config->GetArrayField(TEXT("views")); Routes = Config->GetArrayField(TEXT("routes"));
        bInitialized = true;
    }
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    if (!Pawn || !Streaming)
    {
        if (Now-Started > 60) Finish(false, TEXT("Playable character unavailable"));
        return;
    }
    if (ViewIndex < Views.Num())
    {
        const auto View = Views[ViewIndex]->AsObject();
        FString Error;
        const FName Zone(*View->GetStringField(TEXT("zone")));
        if (!Streaming->EnsureZone(Zone, Error)) { Finish(false, Error); return; }
        if (!Streaming->IsZoneReady(Zone, PC))
        { if (Now-Started>180) Finish(false, TEXT("Zone did not become ready")); return; }
        if (!bPositioned)
        {
            if (!bBefore && !bGmVerified)
            {
                auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
                if (!Editor || !Editor->Open(PC, Error)) { Finish(false, TEXT("GM initialization: ")+Error); return; }
                const FString OwnerDraft=FPaths::ProjectSavedDir()/TEXT("WorldEdit/crownward-draft.json");
                if (IFileManager::Get().FileExists(*OwnerDraft))
                {
                    FString Contents;
                    if (IFileManager::Get().FileSize(*OwnerDraft)>8000000 || !FFileHelper::LoadFileToString(Contents,*OwnerDraft)
                        || !IFileManager::Get().MakeDirectory(*FPaths::GetPath(Editor->GetDraftLocation()),true)
                        || !FFileHelper::SaveStringToFile(Contents,*Editor->GetDraftLocation(),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)
                        || !Editor->LoadDraft(PC,Editor->GetHistory().GetRevision(),Error))
                    { Finish(false,TEXT("Isolated owner draft compatibility: ")+Error); return; }
                    bOwnerDraftImported=true;
                }
                const auto* Object = Editor->GetHistory().GetObjects().FindByPredicate([Editor](const auto& Row) {
                    const auto* Actor=Editor->GetObjectActor(Row.Id);
                    return Actor && Actor->ActorHasTag(TEXT("WarCapitalInterior"));
                });
                if (!Object) { Finish(false, TEXT("New buildings are missing from GM catalog")); return; }
                const FName Id = Object->Id; const FTransform Original = Object->Transform;
                TArray<AActor*> Lights; Editor->GetObjectActor(Id)->GetAttachedActors(Lights);
                TArray<FVector> Locations; for (const auto* Light:Lights) Locations.Add(Light->GetActorLocation());
                FTransform Moved = Original; Moved.AddToTranslation(FVector(10,0,0));
                if (!Editor->Edit(PC, Id, Moved, false, Editor->GetHistory().GetRevision(), Error))
                { Finish(false,TEXT("GM expansion move: ")+Error); return; }
                bLightingFollowsEdit=!Lights.IsEmpty();
                for (int32 I=0;I<Lights.Num();++I) bLightingFollowsEdit &= Lights[I]->GetActorLocation().Equals(Locations[I]+FVector(10,0,0),.001);
                if (!bLightingFollowsEdit) { Finish(false,TEXT("Interior lighting did not follow the GM building move")); return; }
                if (!Editor->Undo(PC, false, Editor->GetHistory().GetRevision(), Error)
                    || !Editor->Undo(PC, true, Editor->GetHistory().GetRevision(), Error)
                    || !Editor->Undo(PC, false, Editor->GetHistory().GetRevision(), Error)
                    || !Editor->GetObjectActor(Id) || !Editor->GetObjectActor(Id)->GetActorTransform().Equals(Original)
                    || !Editor->SaveDraft(PC, Editor->GetHistory().GetRevision(), Error))
                { Finish(false, TEXT("GM expansion edit/undo/redo: ")+Error); return; }
                bGmVerified = true;
            }
            const FVector Feet = ReadVector(View->GetArrayField(TEXT("feet")));
            Pawn->SetActorLocation(Feet+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3), false);
            Pawn->GetCharacterMovement()->StopMovementImmediately();
            const FVector Eye = ReadVector(View->GetArrayField(TEXT("eye")));
            const FVector Target = ReadVector(View->GetArrayField(TEXT("target")));
            if (!Camera.IsValid()) Camera = GetWorld()->SpawnActor<ACameraActor>();
            Camera->SetActorLocationAndRotation(Eye, (Target-Eye).Rotation());
            Camera->GetCameraComponent()->SetFieldOfView(70);
            PC->bAutoManageActiveCameraTarget = false; PC->SetViewTarget(Camera.Get());
            Next = Now+6; bPositioned = true; bCaptured = false;
            return;
        }
        if (Now > Next-3 && DeltaTime > 0) Frames.Add(DeltaTime*1000.0);
        if (Now < Next) return;
        if (!bCaptured)
        {
            FScreenshotRequest::RequestScreenshot(Directory / FString::Printf(TEXT("view_%02d.png"), ViewIndex), false, false);
            bCaptured = true; Next = Now+1; return;
        }
        ++ViewIndex; bPositioned = false; Started = Now; return;
    }
    if (bBefore || RouteIndex >= Routes.Num())
    {
        if (!bBefore)
        {
            auto* Editor=GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FString Error;
            bGmReloadVerified=Editor && Editor->LoadDraft(PC,Editor->GetHistory().GetRevision(),Error);
            if (!bGmReloadVerified) { Finish(false,TEXT("GM draft reload after travel: ")+Error); return; }
        }
        Finish(true, TEXT("Rendered city views and configured walking routes completed")); return;
    }
    const auto Route = Routes[RouteIndex]->AsObject();
    const auto Points = Route->GetArrayField(TEXT("points"));
    FString Error;
    const FName Zone(*Route->GetStringField(TEXT("zone")));
    if (!Streaming->EnsureZone(Zone, Error)) { Finish(false, Error); return; }
    if (!Streaming->IsZoneReady(Zone, PC))
    { if (Now-Started>180) Finish(false, TEXT("Interior zone unavailable")); return; }
    if (!bPositioned)
    {
        if (Points.Num()<2) { Finish(false,TEXT("Interior route missing")); return; }
        const FVector Feet = ReadVector(Points[0]->AsArray());
        Pawn->SetActorLocation(Feet+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3), false);
        Pawn->GetCharacterMovement()->StopMovementImmediately();
        Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        RouteStarted = Now; Waypoint = 1; Next = Now+.5; bPositioned = true; return;
    }
    if (Now<Next) return;
    const FVector Feet=Pawn->GetActorLocation()-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector Target=ReadVector(Points[Waypoint]->AsArray());
    if (Now-RouteStarted>90)
    {
        Finish(false,FString::Printf(TEXT("Interior %s stalled at waypoint %d; feet=%s target=%s"),
            *Route->GetStringField(TEXT("id")),Waypoint,*Feet.ToString(),*Target.ToString())); return;
    }
    if (FVector::Dist2D(Feet,Target)<35 && FMath::Abs(Feet.Z-Target.Z)<50)
    {
        ++Waypoint;
        if (Waypoint>=Points.Num())
        {
            Pawn->GetCharacterMovement()->StopMovementImmediately();
            UE_LOG(LogTemp,Display,TEXT("WAR_EXPANSION_WALKED=%s seconds=%.2f"),*Route->GetStringField(TEXT("id")),Now-RouteStarted);
            ++RouteIndex; bPositioned=false; Started=Now;
        }
        return;
    }
    Pawn->AddMovementInput((Target-Feet).GetSafeNormal2D(), .4f, true);
}
