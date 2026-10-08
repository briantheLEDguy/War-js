#include "WarT1ReviewProof.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarWorldEditMap.h"
#include "WarZoneAnchor.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"

bool UWarT1ReviewProof::ShouldCreateSubsystem(UObject* Outer) const
{
    return !UE_BUILD_SHIPPING && FParse::Param(FCommandLine::Get(), TEXT("WarT1ReviewProof"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentGM")) && Super::ShouldCreateSubsystem(Outer);
}
bool UWarT1ReviewProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type == EWorldType::Game; }
TStatId UWarT1ReviewProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarT1ReviewProof, STATGROUP_Tickables); }

void UWarT1ReviewProof::Finish(bool Passed, const FString& Detail)
{
    bFinished = true;
    if (!Run.IsEmpty())
    {
        const FString Directory = FPaths::ProjectSavedDir() / TEXT("T1ReviewProof") / Run;
        IFileManager::Get().MakeDirectory(*Directory, true);
        auto Report = MakeShared<FJsonObject>();
        Report->SetBoolField(TEXT("passed"), Passed);
        Report->SetStringField(TEXT("detail"), Detail);
        Report->SetStringField(TEXT("map"), GetWorld()->GetPackage()->GetName());
        Report->SetBoolField(TEXT("ordinaryCharacterEntry"), Passed);
        Report->SetBoolField(TEXT("gmFlightAndReturn"), Passed);
        Report->SetBoolField(TEXT("draftWritten"), false);
        Report->SetBoolField(TEXT("visualApproved"), false);
        Report->SetArrayField(TEXT("arrivalCm"), {MakeShared<FJsonValueNumber>(Arrival.X),
            MakeShared<FJsonValueNumber>(Arrival.Y), MakeShared<FJsonValueNumber>(Arrival.Z)});
        FString Json; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
        if (!FFileHelper::SaveStringToFile(Json, *(Directory / TEXT("report.json")))) Passed = false;
    }
    UE_LOG(LogTemp, Display, TEXT("WAR_T1_REVIEW_%s %s"), Passed ? TEXT("PASSED") : TEXT("FAILED"), *Detail);
    FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
}
bool UWarT1ReviewProof::Grounded(AWarCharacter* Pawn) const
{
    if (!Pawn || !Pawn->GetCharacterMovement()->IsMovingOnGround()) return false;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(T1ReviewArrival), true, Pawn);
    const FVector Feet = Pawn->GetActorLocation() - FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    return GetWorld()->LineTraceSingleByChannel(Hit, Feet + FVector(0,0,15), Feet - FVector(0,0,25), ECC_Visibility, Query)
        && Hit.ImpactNormal.Z >= .71 && Hit.GetActor()
        && Hit.GetActor()->ActorHasTag(TEXT("WarT1PrototypeTerrain"));
}
void UWarT1ReviewProof::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < Next) return;
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    if (Now > 60) { Finish(false, TEXT("Entry/recovery timed out.")); return; }
    if (!PC) return;
    if (Step == 0)
    {
        FString Selected, Requested; FGuid Id;
        GConfig->GetString(TEXT("/Script/EngineSettings.GameMapsSettings"), TEXT("GameDefaultMap"), Selected, GEngineIni);
        if (GetWorld()->GetNetMode() != NM_Standalone || !WarWorldEditMap::IsT1HumanReview(Selected)
            || GetWorld()->GetPackage()->GetName() != Selected
            || !FParse::Value(FCommandLine::Get(), TEXT("WarT1ReviewRun="), Requested)
            || !FGuid::ParseExact(Requested, EGuidFormats::Digits, Id))
        { Finish(false, TEXT("Proof requires an exact selected private T1 map, local authority and run.")); return; }
        Run = Id.ToString(EGuidFormats::Digits);
        IFileManager::Get().MakeDirectory(*(FPaths::ProjectSavedDir() / TEXT("T1ReviewProof") / Run), true);
        const bool Sun = Selected.Contains(TEXT("/sunmeadow_march/"));
        auto* Visual = LoadObject<UWarCharacterVisualDefinition>(nullptr, Sun
            ? TEXT("/Game/MigrationProof/Visual_civic_sunfire_templar_m") : TEXT("/Game/MigrationProof/Visual_mire_warbrute_m"));
        if (!Visual) { Finish(false, TEXT("Exact regional playable visual unavailable.")); return; }
        PC->ServerCreateDevelopmentCharacter_Implementation(TEXT("Terrain Reviewer"), Visual->RaceId, Visual->ClassId, Visual->BodyVariant);
        UE_LOG(LogTemp, Display, TEXT("WAR_T1_REVIEW_ENTRY_REQUESTED %s"), *Selected);
        Step = 1; Next = Now + 2; return;
    }
    auto* Pawn = Cast<AWarCharacter>(PC->GetPawn());
    if (!PC->GetEntryFailure().IsEmpty()) { Finish(false, PC->GetEntryFailure().ToString()); return; }
    if (!Pawn || !Pawn->IsVisualReady()) { Next = Now + .2; return; }
    if (!PC->CanUseGmTools()) { Finish(false, TEXT("Ordinary local entry did not admit GM recovery tools.")); return; }
    if (Step == 1)
    {
        if (!Grounded(Pawn)) { Finish(false, TEXT("Ordinary character arrival is not grounded on native terrain.")); return; }
        Arrival = Pawn->GetActorLocation();
        PC->ServerSetDevelopmentTraversal_Implementation(true,1);
        if (!Pawn->IsDevelopmentFlying()) { Finish(false, TEXT("GM flight was rejected.")); return; }
        Pawn->SetActorLocation(Arrival - FVector(0,0,2500), false, nullptr, ETeleportType::TeleportPhysics);
        PC->ServerReturnToDevelopmentSpawn_Implementation();
        if (FVector::Dist(Pawn->GetActorLocation(),Arrival) > 15)
        { Finish(false, TEXT("GM return could not recover from below the terrain.")); return; }
        PC->ServerSetDevelopmentTraversal_Implementation(false,1);
        if (Pawn->IsDevelopmentFlying()) { Finish(false, TEXT("GM could not return to walking.")); return; }
        Step = 2; Next = Now + 3; return;
    }
    if (!Grounded(Pawn) || FVector::Dist(Pawn->GetActorLocation(),Arrival) > 20)
    { Finish(false, TEXT("Recovered character did not remain grounded.")); return; }
    if (Step == 2 && GetWorld()->GetGameViewport())
    {
        FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("T1ReviewProof") / Run / TEXT("grounded.png"), true, false);
        Step = 3; Next = Now + 1; return;
    }
    Finish(true, TEXT("Ordinary frontend character entry, grounded arrival, local GM flight and below-terrain return passed."));
}
