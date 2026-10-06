#include "WarSiegePlaytestProof.h"
#include "WarSiegeGameMode.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeNavigation.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAbilityRuntime.h"
#include "WarAbilityCatalog.h"
#include "WarAttributeSet.h"
#include "WarWarpIdol.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Net/UnrealNetwork.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace
{
    bool Enabled()
    {
        return !UE_BUILD_SHIPPING && FParse::Param(FCommandLine::Get(),TEXT("WarSiegeAutomation"))
            && FParse::Param(FCommandLine::Get(),TEXT("WarSiegePlaytest"))
            && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentNetworking"));
    }
    FString Folder()
    {
        FString Run,Role; FParse::Value(FCommandLine::Get(),TEXT("WarSiegeProofRun="),Run);
        FParse::Value(FCommandLine::Get(),TEXT("WarSiegeProofRole="),Role);
        FGuid Id;
        if (!FGuid::Parse(Run,Id) || (Role!=TEXT("aegis") && Role!=TEXT("riftbound") && Role!=TEXT("server"))) return {};
        return FPaths::ProjectSavedDir()/TEXT("SiegePlaytestProof")/Id.ToString(EGuidFormats::Digits)/Role;
    }
}
AWarSiegeTestDriver::AWarSiegeTestDriver()
{ bReplicates=true; bOnlyRelevantToOwner=true; PrimaryActorTick.bCanEverTick=true; SetNetUpdateFrequency(10); }
void AWarSiegeTestDriver::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarSiegeTestDriver,Waypoint); DOREPLIFETIME(AWarSiegeTestDriver,bMove); DOREPLIFETIME(AWarSiegeTestDriver,Enemy);
}
void AWarSiegeTestDriver::Tick(float Delta)
{
    Super::Tick(Delta); if (!Enabled()) return;
    auto* PC=Cast<AWarPlayerController>(GetOwner());
    auto* Pawn=PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    const auto* GS=GetWorld()->GetGameState<AWarSiegeGameState>();
    if (!GS || GS->Siege.Phase!=EWarSiegePhase::Active || !Pawn || Pawn->IsDead() || !Pawn->IsVisualReady()) return;
    const double Now=GetWorld()->GetTimeSeconds();
    if (HasAuthority())
    {
        if (Now<NextPath) return; NextPath=Now+.25;
        // Exercise a different legitimate tactic in round two: defenders cover
        // the optional emplacement while attackers continue the main escort.
        const bool CoverEmplacement=GS->RoundId==2 && PC->GetPlayerState<AWarPlayerState>()->GetRealm()==EWarRealm::Aegis;
        const FVector Objective=CoverEmplacement ? GS->OptionalLocation : GS->ObjectiveLocation;
        Enemy=nullptr; double Nearest=FMath::Square(2200.);
        for (TActorIterator<AWarCharacter> It(GetWorld());It;++It)
        {
            if (CoverEmplacement && FVector::Dist2D(It->GetActorLocation(),Objective)>2000) continue;
            const double Distance=FVector::DistSquared(Pawn->GetActorLocation(),It->GetActorLocation());
            if (Distance<Nearest && Pawn->CanAbilityTarget(*It,2200)) { Enemy=*It; Nearest=Distance; }
        }
        auto* Mode=GetWorld()->GetAuthGameMode<AWarSiegeGameMode>(); if (!Mode || !Mode->IsDevelopmentPlaytest()) return;
        const bool Caster=Pawn->GetCareerId()==TEXT("ember_arcanist") || Pawn->GetCareerId()==TEXT("ruin_oracle") || Pawn->GetCareerId()==TEXT("void_magister");
        bMove=!Enemy || Nearest>FMath::Square(Caster ? 1100.f : 150.f);
        FVector Goal=Enemy ? Enemy->GetActorLocation() : Objective;
        if (!Enemy && Mode->Battlefield)
            if (!WarSiegeNavigation::Approach(Pawn,Goal,FVector(0,PC->GetPlayerState<AWarPlayerState>()->GetRealm()==EWarRealm::Aegis ? 400 : -400,0),Mode->Battlefield->ObjectiveRadius,Goal)) bMove=false;
        if (bMove)
        {
            const auto* Path=UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(),Pawn->GetActorLocation(),Goal,Pawn);
            bMove=Path && Path->IsValid() && !Path->IsPartial() && Path->PathPoints.Num()>1;
            if (bMove)
            {
                int32 Index=1;
                while (Index<Path->PathPoints.Num()-1 && FVector::Dist2D(Pawn->GetActorLocation(),Path->PathPoints[Index])<150) ++Index;
                Waypoint=Path->PathPoints[Index];
                if (FVector::Dist2D(Pawn->GetActorLocation(),Goal)<80) bMove=false;
            }
        }
        ForceNetUpdate(); return;
    }
    if (!PC->IsLocalController()) return;
    if (PreviousPawn==Pawn) Travelled+=FVector::Dist2D(Pawn->GetActorLocation(),PreviousPosition);
    PreviousPawn=Pawn; PreviousPosition=Pawn->GetActorLocation();
    auto* Runtime=PC->GetPlayerState<AWarPlayerState>()->GetClassAbilities();
    if (bMove && !Runtime->IsBusy() && !Pawn->IsActionPlaying() && FVector::Dist2D(Pawn->GetActorLocation(),Waypoint)>60)
        Pawn->AddMovementInput((Waypoint-Pawn->GetActorLocation()).GetSafeNormal2D());
    FVector Look=Enemy ? Enemy->GetActorLocation()-Pawn->GetActorLocation() : Waypoint-Pawn->GetActorLocation();
    if (!Look.IsNearlyZero()) { auto Rotation=Look.Rotation(); Rotation.Pitch=-12; PC->SetControlRotation(Rotation); }
    if (!Enemy || Now<NextAction || Runtime->IsBusy()) return;
    NextAction=Now+.6;
    for (int32 I=0;I<32 && PC->GetCombatTarget()!=Enemy;++I) PC->CycleCombatTarget();
    const auto* Catalog=GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    if (!Catalog) return;
    const auto Kit=Catalog->Kit(Pawn->GetCareerId());
    for (const auto* A:Kit)
    {
        if (Runtime->Cooldown(A->Id)>0 || !A->UnavailableReason.IsEmpty()) continue;
        bool Use=A->Effects.ContainsByPredicate([](const auto& E){return E.Kind==TEXT("damage") || E.Kind==TEXT("status");});
        if (A->Id==TEXT("void_magister.summon_idol")) Use=!AWarWarpIdol::HasFor(Pawn);
        if (A->Effects.ContainsByPredicate([](const auto& E){return E.Kind==TEXT("heal");}))
        { const auto* Attributes=PC->GetPlayerState<AWarPlayerState>()->GetAttributes(); Use=Attributes->GetHealth()<Attributes->GetMaxHealth()*.7; }
        FString Error; AActor* Target=A->bEnemyTarget ? static_cast<AActor*>(Enemy) : Pawn;
        if (Use && Runtime->CanActivate(*A,Target,Error))
        { Runtime->ServerActivate(A->Id,Target); ++ActionRequests; break; }
    }
}
bool UWarSiegePlaytestProof::ShouldCreateSubsystem(UObject* Outer) const
{ return Super::ShouldCreateSubsystem(Outer) && Enabled(); }
bool UWarSiegePlaytestProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type==EWorldType::Game; }
TStatId UWarSiegePlaytestProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarSiegePlaytestProof,STATGROUP_Tickables); }
void UWarSiegePlaytestProof::Capture(const FString& Name)
{
    if (Folder().IsEmpty()) return;
    IFileManager::Get().MakeDirectory(*Folder(),true);
    FScreenshotRequest::RequestScreenshot(Folder()/(Name+TEXT(".png")),true,false);
}
void UWarSiegePlaytestProof::Finish(bool Passed,const FString& Detail)
{
    Finished=true; auto Report=MakeShared<FJsonObject>();
    Report->SetBoolField(TEXT("passed"),Passed); Report->SetStringField(TEXT("detail"),Detail);
    Report->SetBoolField(TEXT("humanPlaytest"),false); Report->SetBoolField(TEXT("releaseApproved"),false);
    Report->SetArrayField(TEXT("rounds"),RoundReports);
    double Distance=0; int32 Actions=0;
    for (TActorIterator<AWarSiegeTestDriver> It(GetWorld());It;++It) { Distance+=It->Travelled; Actions+=It->ActionRequests; }
    Report->SetNumberField(TEXT("movementCm"),Distance); Report->SetNumberField(TEXT("actionRequests"),Actions);
    Report->SetBoolField(TEXT("passed"),Passed && Results.Num()==3 && ActiveRounds.Num()==3 && Distance>1000 && Actions>0);
    FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(Folder()/TEXT("report.json")));
    UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_AUTOMATION_COMPLETE results=%d distance=%.1f actions=%d"),Results.Num(),Distance,Actions);
}
void UWarSiegePlaytestProof::Tick(float Delta)
{
    if (Finished || !GetWorld()->HasBegunPlay()) return;
    auto* GS=GetWorld()->GetGameState<AWarSiegeGameState>(); if (!GS || !GS->bDevelopmentLobby) return;
    if (auto* Mode=GetWorld()->GetAuthGameMode<AWarSiegeGameMode>())
    {
        if (!Mode->IsDevelopmentPlaytest()) return;
        for (auto It=GetWorld()->GetPlayerControllerIterator();It;++It) if (!Drivers.Contains(It->Get()))
        { FActorSpawnParameters Params; Params.Owner=It->Get(); GetWorld()->SpawnActor<AWarSiegeTestDriver>(Params); Drivers.Add(It->Get()); }
        if (GetWorld()->GetTimeSeconds()>=NextSnapshot && !Folder().IsEmpty())
        {
            NextSnapshot=GetWorld()->GetTimeSeconds()+10;
            auto Snapshot=MakeShared<FJsonObject>();
            Snapshot->SetNumberField(TEXT("round"),GS->RoundId);
            Snapshot->SetNumberField(TEXT("elapsed"),GS->Siege.Elapsed);
            Snapshot->SetNumberField(TEXT("objective"),GS->Siege.Objective);
            Snapshot->SetNumberField(TEXT("progress"),GS->Siege.Progress);
            Snapshot->SetBoolField(TEXT("contested"),GS->bContested);
            Snapshot->SetStringField(TEXT("goal"),Mode->TaskLocation().ToString());
            TArray<TSharedPtr<FJsonValue>> Actors;
            for (TActorIterator<AWarCharacter> It(GetWorld());It;++It)
            {
                const auto* State=It->GetPlayerState<AWarPlayerState>(); if (!State) continue;
                auto Row=MakeShared<FJsonObject>();
                Row->SetStringField(TEXT("name"),State->GetPlayerName());
                Row->SetStringField(TEXT("class"),It->GetCareerId().ToString());
                Row->SetStringField(TEXT("position"),It->GetActorLocation().ToString());
                Row->SetNumberField(TEXT("speed"),It->GetVelocity().Size());
                Row->SetNumberField(TEXT("health"),State->GetAttributes()->GetHealth());
                if (const auto* Unit=Cast<AWarSiegeCharacter>(*It)) Row->SetNumberField(TEXT("unit"),int32(Unit->Unit));
                if (const auto* Bot=Cast<AWarSiegeBotController>(It->GetController())) Row->SetNumberField(TEXT("moveStatus"),int32(Bot->GetMoveStatus()));
                Actors.Add(MakeShared<FJsonValueObject>(Row));
            }
            Snapshot->SetArrayField(TEXT("actors"),Actors);
            FString Json; FJsonSerializer::Serialize(Snapshot,TJsonWriterFactory<>::Create(&Json));
            IFileManager::Get().MakeDirectory(*Folder(),true);
            FFileHelper::SaveStringToFile(Json,*(Folder()/TEXT("state.json")));
        }
        return;
    }
    auto* PC=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    if (!PC || !PC->IsLocalController() || Folder().IsEmpty()) return;
    const double Now=GetWorld()->GetTimeSeconds();
    const int32 Phase=int32(GS->Siege.Phase);
    if (PreviousRound!=GS->RoundId || PreviousPhase!=Phase)
    { PreviousRound=GS->RoundId; PreviousPhase=Phase; PhaseAt=Now; NextLobbyAction=Now+6; }
    if (GS->Siege.Phase==EWarSiegePhase::Active)
    {
        ActiveRounds.Add(GS->RoundId);
        if (Now-PhaseAt>20 && !CombatCaptures.Contains(GS->RoundId))
        { Capture(FString::Printf(TEXT("round-%d-active"),GS->RoundId)); CombatCaptures.Add(GS->RoundId); }
        if (Now-PhaseAt>30 && PC->GetCombatTarget() && !TargetCaptures.Contains(GS->RoundId))
        { Capture(FString::Printf(TEXT("round-%d-combat"),GS->RoundId)); TargetCaptures.Add(GS->RoundId); }
        if (Now>=NextSnapshot)
        { Capture(FString::Printf(TEXT("round-%d-live"),GS->RoundId)); NextSnapshot=Now+60; }
        return;
    }
    if (GS->Siege.Phase!=EWarSiegePhase::Waiting && GS->Siege.Phase!=EWarSiegePhase::Finished) return;
    if (Now<NextLobbyAction) return; NextLobbyAction=Now+6;
    Capture(FString::Printf(TEXT("round-%d-lobby"),GS->RoundId));
    if (GS->Siege.Phase==EWarSiegePhase::Finished && !Results.Contains(GS->RoundId))
    {
        Results.Add(GS->RoundId); auto Row=MakeShared<FJsonObject>();
        Row->SetNumberField(TEXT("round"),GS->RoundId); Row->SetNumberField(TEXT("elapsed"),GS->Siege.Elapsed);
        Row->SetNumberField(TEXT("deaths"),GS->Deaths); Row->SetNumberField(TEXT("milestones"),GS->Siege.MilestoneSeconds.Num());
        Row->SetBoolField(TEXT("attackersWon"),GS->Siege.bAttackersWon); RoundReports.Add(MakeShared<FJsonValueObject>(Row));
        UE_LOG(LogTemp,Display,TEXT("WAR_SIEGE_AUTOMATION_RESULT round=%d"),GS->RoundId);
        return;
    }
    if (Results.Num()==3) { Finish(true,TEXT("Three normal-timed network rounds and rematches observed with client movement and ability requests.")); return; }
    if (!GS->bContentReady) return;
    if (SelectedForRound!=GS->RoundId)
    { PC->ServerSiegeSelectRole(GS->RoundId,uint8((GS->RoundId+2)%3)); SelectedForRound=GS->RoundId; return; }
    PC->ServerSiegeReady(GS->RoundId,true);
}
