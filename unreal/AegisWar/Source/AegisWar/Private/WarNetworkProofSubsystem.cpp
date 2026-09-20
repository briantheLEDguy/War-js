#include "WarNetworkProofSubsystem.h"
#include "AegisWar.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

bool UWarNetworkProofSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer)
        && FParse::Param(FCommandLine::Get(), TEXT("WarNetworkProof"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentNetworking"));
#endif
}

bool UWarNetworkProofSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game;
}

TStatId UWarNetworkProofSubsystem::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(UWarNetworkProofSubsystem, STATGROUP_Tickables);
}

void UWarNetworkProofSubsystem::Finish(const bool bPassed, const FString& Detail)
{
    bFinished = true;
    FString Run;
    FParse::Value(FCommandLine::Get(), TEXT("WarProofRun="), Run);
    if (Run.IsEmpty() || Run.Contains(TEXT("..")) || Run.Contains(TEXT("/")) || Run.Contains(TEXT("\\"))) return;
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("NetworkProof"), Run);
    IFileManager::Get().MakeDirectory(*Directory, true);
    const TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
    Report->SetNumberField(TEXT("schemaVersion"), 1);
    Report->SetBoolField(TEXT("passed"), bPassed);
    Report->SetStringField(TEXT("role"), ResultRole);
    Report->SetStringField(TEXT("detail"), Detail);
    Report->SetBoolField(TEXT("observedReplicatedMovement"), bMoved);
    Report->SetBoolField(TEXT("autonomousProxy"), bAutonomous);
    Report->SetBoolField(TEXT("movementAnimation"), bMovementAnimation);
    Report->SetBoolField(TEXT("strikeAnimation"), bStrikeAnimation);
    Report->SetNumberField(TEXT("defenderHealth"), ObservedHealth);
    Report->SetNumberField(TEXT("attackerMana"), ObservedMana);
    Report->SetNumberField(TEXT("strikeRequests"), StrikeRequests);
    Report->SetBoolField(TEXT("graphicalAcceptance"), false);
    FString Json;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    const FString Filename = FPaths::Combine(Directory, ResultRole + TEXT(".json"));
    if (!FFileHelper::SaveStringToFile(Json, *Filename))
    {
        UE_LOG(LogAegisWar, Error, TEXT("Could not save network proof: %s"), *Filename);
        return;
    }
    UE_LOG(LogAegisWar, Display, TEXT("WAR_NETWORK_PROOF %s passed=%d %s"), *ResultRole, bPassed, *Detail);
    if (GetWorld()->GetNetMode() == NM_Client && FParse::Param(FCommandLine::Get(), TEXT("WarProofScreenshot")))
        FScreenshotRequest::RequestScreenshot(FPaths::Combine(Directory, ResultRole + TEXT(".png")), false, false);
}

void UWarNetworkProofSubsystem::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (StartedAt < 0) StartedAt = Now;
    const bool bServer = GetWorld()->GetNetMode() == NM_DedicatedServer;
    ResultRole = bServer ? TEXT("server") : TEXT("client-pending");
    AWarCharacter* Attacker = nullptr;
    AWarCharacter* Defender = nullptr;
    for (TActorIterator<AWarCharacter> It(GetWorld()); It; ++It)
    {
        const AWarPlayerState* State = It->GetPlayerState<AWarPlayerState>();
        if (!State || !It->IsVisualReady() || !It->GetMesh()->GetSkeletalMeshAsset()) continue;
        if (State->GetRealm() == EWarRealm::Aegis) Attacker = *It;
        if (State->GetRealm() == EWarRealm::Riftbound) Defender = *It;
    }
    if (!Attacker || !Defender)
    {
        if (Now - StartedAt > 75) Finish(false, TEXT("Two replicated authored characters did not become ready."));
        return;
    }
    const AWarPlayerState* Aegis = Attacker->GetPlayerState<AWarPlayerState>();
    const AWarPlayerState* Riftbound = Defender->GetPlayerState<AWarPlayerState>();
    ObservedHealth = Riftbound->GetAttributes()->GetHealth();
    ObservedMana = Aegis->GetAttributes()->GetMana();
    const bool bAttackerClient = !bServer && Attacker->IsLocallyControlled();
    const bool bDefenderClient = !bServer && Defender->IsLocallyControlled();
    if (!bServer && !bAttackerClient && !bDefenderClient) return;
    ResultRole = bServer ? TEXT("server") : bAttackerClient ? TEXT("client-aegis") : TEXT("client-riftbound");
    bAutonomous = !bServer && (bAttackerClient ? Attacker : Defender)->GetLocalRole() == ROLE_AutonomousProxy;
    if (PairReadyAt < 0)
    {
        if (ObservedHealth < 99.f || (bAttackerClient && ObservedMana < 99.f)) return;
        PairReadyAt = Now;
        InitialAttackerPosition = Attacker->GetActorLocation();
    }
    bMoved |= FVector::Dist2D(InitialAttackerPosition, Attacker->GetActorLocation()) > 50.f;
    bMovementAnimation |= Attacker->GetPlayingAnimation() == TEXT("walk") || Attacker->GetPlayingAnimation() == TEXT("run");
    bStrikeAnimation |= Attacker->GetPlayingAnimation() == TEXT("attack_melee");
    const double Elapsed = Now - PairReadyAt;
    if (bAttackerClient)
    {
        if (Elapsed < 0.35) Attacker->AddMovementInput(FVector(0, 1, 0));
        if ((StrikeRequests == 0 && Elapsed > 1.0) || (StrikeRequests == 1 && Elapsed > 1.3))
        {
            Attacker->RequestTargetStrike(Defender);
            ++StrikeRequests;
        }
    }
    if (Elapsed > 2.0 && bMoved && FMath::IsNearlyEqual(ObservedHealth, 80.f)
        && ((!bServer && !bAttackerClient) || FMath::IsNearlyEqual(ObservedMana, 90.f))
        && (bServer || (bAutonomous && bMovementAnimation && bStrikeAnimation)))
    {
        Finish(true, TEXT("Authored character replication, movement, server damage and duplicate cooldown request verified."));
    }
    else if (Elapsed > 20)
    {
        Finish(false, FString::Printf(TEXT("Acceptance timed out; distance=%.1f health=%.1f mana=%.1f moved=%d autonomous=%d attacker=%s defender=%s falling=%d"),
            FVector::Dist(Attacker->GetActorLocation(), Defender->GetActorLocation()), ObservedHealth, ObservedMana, bMoved, bAutonomous,
            *Attacker->GetActorLocation().ToString(), *Defender->GetActorLocation().ToString(), Attacker->GetCharacterMovement()->IsFalling()));
    }
}
