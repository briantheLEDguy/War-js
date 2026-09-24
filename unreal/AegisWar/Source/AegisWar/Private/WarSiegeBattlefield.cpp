#include "WarSiegeBattlefield.h"
#include "WarCharacterVisualDefinition.h"
#include "WarContentSubsystem.h"
#include "WarAbilityCatalog.h"
#include "Components/SceneComponent.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Components/StaticMeshComponent.h"
#include "Net/UnrealNetwork.h"

AWarSiegeBattlefield::AWarSiegeBattlefield()
{ RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("SiegeOrigin")); bReplicates = true; bAlwaysRelevant = true; }
FVector AWarSiegeBattlefield::Objective(int32 Stage, int32 Step) const
{
    const int32 Index = Stage == 0 ? Step : Stage == 1 ? 4 + Step : 7;
    return Objectives.IsValidIndex(Index) ? Objectives[Index] : FVector::ZeroVector;
}
bool AWarSiegeBattlefield::Validate(FString& Error) const
{
    auto Fail = [&Error](const FString& Why) { Error = Why; return false; };
    if (DefinitionVersion != 1 || Capital != TEXT("aegis_capital")) return Fail(TEXT("Unsupported siege definition or capital."));
    if (Objectives.Num() != 8 || OptionalObjectives.Num() != 3 || TeamSpawns.Num() != 6)
        return Fail(TEXT("Siege requires eight objective anchors, three optional anchors and six team spawns."));
    if (StageGates.Num() != 2 || GateMechanisms.Num() != 2 || WarEffortProps.Num() != 3)
        return Fail(TEXT("Bind two visible stage gates, two gate mechanisms and three war-effort props in the isolated siege map."));
    TArray<TObjectPtr<AActor>> Props = StageGates; Props.Append(GateMechanisms); Props.Append(WarEffortProps);
    TSet<AActor*> Seen;
    for (const auto& Pointer : Props)
    {
        AActor* Prop = Pointer.Get();
        const auto* Mesh = IsValid(Prop) ? Prop->FindComponentByClass<UStaticMeshComponent>() : nullptr;
        if (!Mesh || !Mesh->GetStaticMesh() || Seen.Contains(Prop) || Prop->GetLevel() != GetLevel())
            return Fail(TEXT("Siege props require distinct authored meshes in the isolated persistent level."));
        Seen.Add(Prop);
    }
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        const FString Class = It->GetClass()->GetName();
        if (Class == TEXT("WarEnemy") || Class == TEXT("WarQuestNpc") || Class == TEXT("WarCityNpc")
            || Class == TEXT("WarResourceNode") || Class == TEXT("WarCraftingStation") || Class == TEXT("WarZonePortal"))
            return Fail(TEXT("The siege map still contains campaign gameplay actors; isolate its content before launch."));
    }
    if (!bTraversalReviewed || !bEquippedRosterReviewed) return Fail(TEXT("Siege traversal and equipped roster review are outstanding."));
    if (!FMath::IsFinite(ObjectiveRadius) || ObjectiveRadius < 200 || ObjectiveRadius > 1000
        || !FMath::IsFinite(ReferenceDamagePerSecond) || ReferenceDamagePerSecond <= 0)
        return Fail(TEXT("Invalid siege radius or reference damage."));
    const auto* Content = GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
    const auto* Catalog = GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    if (!Content || !Content->IsContentReady() || !Catalog || !Catalog->GetError().IsEmpty()) return Fail(TEXT("Siege content or ability catalog is unavailable."));
    bool Roles[2][3] = {};
    for (const auto& Entry : Roster)
    {
        auto* Visual = Entry.Visual.LoadSynchronous();
        if ((Entry.Realm != EWarRealm::Aegis && Entry.Realm != EWarRealm::Riftbound) || int32(Entry.CombatRole) > 2)
            return Fail(TEXT("Invalid bot realm or role."));
        if (!Visual || !Visual->ValidateForSpawn(Entry.Realm, Error) || !Content->ValidatePlayableVisual(Visual, Error))
            return Fail(TEXT("Siege bot visual is missing or unapproved: ") + Error);
        const auto Kit = Catalog->Kit(Visual->ClassId);
        if (Kit.IsEmpty()) return Fail(TEXT("Siege bot has no native class kit."));
        bool Heal = false;
        for (const auto* Ability : Kit)
        {
            if (!Ability->UnavailableReason.IsEmpty()) return Fail(TEXT("Siege bot ability unavailable: ") + Ability->UnavailableReason);
            for (const auto& Effect : Ability->Effects) Heal |= Effect.Kind == TEXT("heal");
        }
        if (Entry.CombatRole == EWarSiegeRole::Healer && !Heal) return Fail(TEXT("Healer roster entry lacks a native heal."));
        Roles[Entry.Realm == EWarRealm::Aegis ? 0 : 1][int32(Entry.CombatRole)] = true;
    }
    for (const auto& Team : Roles) for (bool Present : Team) if (!Present) return Fail(TEXT("Both realms need approved tank, healer and damage roster entries."));
    const TSoftObjectPtr<UWarCharacterVisualDefinition> Visuals[] = { CrewVisual, GuardVisual, CommanderVisual };
    for (int32 I = 0; I < 3; ++I)
    {
        auto* Visual = Visuals[I].LoadSynchronous();
        if (!Visual || !Visual->ValidateForSpawn(I == 0 ? EWarRealm::Riftbound : EWarRealm::Aegis, Error)
            || !Content->ValidateNpcVisual(Visual, Visual->ProfileKey, Error))
            return Fail(TEXT("Required siege encounter model is unavailable: ") + Error);
    }
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    if (!Nav) return Fail(TEXT("Siege navigation is not built."));
    TArray<FVector> Points = Objectives; Points.Append(OptionalObjectives); Points.Append(TeamSpawns);
    for (const auto& P : Points)
    {
        FNavLocation Projected;
        if (P.ContainsNaN() || !Nav->ProjectPointToNavigation(P, Projected, FVector(100,100,250))
            || FVector::Dist2D(P, Projected.Location) > 100)
            return Fail(TEXT("Siege anchor has no reachable navigation surface."));
        // A zero-length query is not a valid path in Recast; projection suffices.
        if (FVector::DistSquared(Objectives[0], Projected.Location) < FMath::Square(100.f)) continue;
        auto* Path = UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(), Objectives[0], Projected.Location);
        if (!Path || !Path->IsValid() || Path->IsPartial()) return Fail(TEXT("Siege route is disconnected."));
    }
    for (int32 Stage = 0; Stage < 3; ++Stage)
    {
        if (FVector::Dist(TeamSpawns[Stage * 2], TeamSpawns[Stage * 2 + 1]) < 3000)
            return Fail(TEXT("Siege opposing spawns must be separated by at least 30 metres."));
        for (int32 Team = 0; Team < 2; ++Team)
        {
            const FVector Spawn = TeamSpawns[Stage * 2 + Team];
            for (int32 Step = 0; Step <= WarSiege::FinalObjective(Stage); ++Step)
                if (FVector::Dist(Spawn, Objective(Stage, Step)) < ObjectiveRadius + 800)
                    return Fail(TEXT("Siege spawn protection overlaps an objective."));
            if (FVector::Dist(Spawn, OptionalObjectives[Stage]) < ObjectiveRadius + 800)
                return Fail(TEXT("Siege spawn protection overlaps an optional objective."));
        }
    }
    Error.Reset(); return true;
}
void AWarSiegeBattlefield::ApplyMilestones(const FWarSiegeState& State)
{
    if (!HasAuthority()) return;
    OpenGates = State.Phase == EWarSiegePhase::Waiting ? 0 : State.Stage >= 2 ? 3 : State.Stage == 1 ? 1 : 0;
    if (State.Phase == EWarSiegePhase::Transition) OpenGates |= 1 << State.Stage;
    OnRep_Gates(); ForceNetUpdate();
}
void AWarSiegeBattlefield::OnRep_Gates()
{
    for (int32 I = 0; I < StageGates.Num(); ++I) if (IsValid(StageGates[I]))
    { const bool Open = (OpenGates & (1 << I)) != 0; StageGates[I]->SetActorHiddenInGame(Open); StageGates[I]->SetActorEnableCollision(!Open); }
}
void AWarSiegeBattlefield::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{ Super::GetLifetimeReplicatedProps(OutLifetimeProps); DOREPLIFETIME(AWarSiegeBattlefield, OpenGates); }
void AWarSiegeGameState::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarSiegeGameState, Siege); DOREPLIFETIME(AWarSiegeGameState, Status);
    DOREPLIFETIME(AWarSiegeGameState, NextWaveAt); DOREPLIFETIME(AWarSiegeGameState, ObjectiveLocation);
    DOREPLIFETIME(AWarSiegeGameState, OptionalLocation); DOREPLIFETIME(AWarSiegeGameState, HazardLocation);
    DOREPLIFETIME(AWarSiegeGameState, HazardUntil); DOREPLIFETIME(AWarSiegeGameState, CommanderAction);
    DOREPLIFETIME(AWarSiegeGameState, RosterLabels);
}
