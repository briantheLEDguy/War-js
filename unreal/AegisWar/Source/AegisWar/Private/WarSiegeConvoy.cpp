#include "WarSiegeEncounter.h"
#include "WarSiegeEquipment.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "WarSiegeNavigation.h"
#include "Components/CapsuleComponent.h"

bool AWarSiegeEncounter::ValidateEquipmentStaging(FString& Error)
{
    TArray<AWarSiegeEquipment*> Probes;
    bool Clear=Battlefield && Battlefield->EquipmentSpawns.Num()==2 && Battlefield->EquipmentDefinitions.Num()==2;
    for (int32 I=0;Clear && I<2;++I)
    {
        auto* Engine=GetWorld()->SpawnActor<AWarSiegeEquipment>(Battlefield->EquipmentSpawns[I],FRotator::ZeroRotator);
        if (!Engine) { Clear=false;break; }
        Probes.Add(Engine);
        Clear=Engine->Initialize(Battlefield->EquipmentDefinitions[I].LoadSynchronous()) && Engine->IsPlaced();
        // Crew grips may intersect their own chassis; all other geometry still blocks.
        Engine->SetActorEnableCollision(false);
        const auto* Capsule=GetDefault<AWarCharacter>()->GetCapsuleComponent();
        for (int32 Seat=0;Clear && Seat<2;++Seat)
        {
            FVector Center;
            Clear=WarSiegeNavigation::SpawnCandidate(GetWorld(),Engine->CrewPosition(Seat),
                Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight(),Center);
        }
        Engine->SetActorEnableCollision(true);
    }
    for (auto* Engine:Probes) Engine->Destroy();
    if (!Clear) Error=TEXT("Siege staging is obstructed or invalid. Clear the equipment and engineer positions, validate the map, and retry.");
    return Clear;
}

bool AWarSiegeEncounter::ConvoyAlive() const
{
    if (Convoy.Num()!=2) return false;
    for (const auto& Vehicle:Convoy) if (!IsValid(Vehicle) || !Vehicle->HasCrew()) return false;
    return true;
}
bool AWarSiegeEncounter::PrepareConvoy()
{
    if (Convoy.IsEmpty())
    {
        if (Battlefield->EquipmentSpawns.Num()!=2) { FailMatch(TEXT("Two clear equipment staging positions are required.")); return false; }
        for (int32 I=0;I<2;++I)
        {
            auto* Vehicle=GetWorld()->SpawnActor<AWarSiegeEquipment>(Battlefield->EquipmentSpawns[I],FRotator::ZeroRotator);
            if (!Vehicle || !Vehicle->Initialize(Battlefield->EquipmentDefinitions[I].LoadSynchronous()))
            { if (Vehicle) Vehicle->Destroy(); FailMatch(TEXT("Siege equipment could not load. Repair the convoy content and relaunch.")); return false; }
            Vehicle->SetOwner(this); Convoy.Add(Vehicle);
        }
    }
    for (const auto& Vehicle:Convoy) if (!Vehicle->TryPlace()) return true;
    if (GetWorld()->GetTimeSeconds()<CrewAt) return true;
    for (const auto& Vehicle:Convoy) for (int32 Seat=0;Seat<2;++Seat)
    {
        if (IsValid(Vehicle->Engineers[Seat]) && !Vehicle->Engineers[Seat]->IsDead()) continue;
        // Replacement crew wait for occupied grips to clear; never teleport onto a participant.
        const auto* Capsule=GetDefault<AWarCharacter>()->GetCapsuleComponent();FVector Center;
        Vehicle->SetActorEnableCollision(false);
        const bool Clear=WarSiegeNavigation::SpawnCandidate(GetWorld(),Vehicle->CrewPosition(Seat),
            Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight(),Center);
        Vehicle->SetActorEnableCollision(true);
        if (!Clear) return true;
        auto* Engineer=SpawnUnit(EWarRealm::Riftbound,EWarSiegeRole::Damage,EWarSiegeUnit::Crew,
            Battlefield->CrewVisual.LoadSynchronous(),Vehicle->CrewPosition(Seat));
        if (!Engineer || !Vehicle->BindEngineer(Seat,Cast<AWarSiegeCharacter>(Engineer->GetPawn())))
        { FailMatch(TEXT("Engineer placement failed. Clear the convoy route and relaunch.")); return false; }
        auto* PS=Engineer->GetPlayerState<AWarPlayerState>();
        // Preserve the previous total crew health budget across four exposed engineers.
        const float Health=Battlefield->ReferenceDamagePerSecond*10*WarSiege::HealthScale(SiegeState()->Siege.Capacity);
        PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),Health);
        PS->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),Health);
    }
    return true;
}
void AWarSiegeEncounter::DriveConvoy(const FWarSiegePresence& P,float Delta)
{
    if (Convoy.Num()!=2) return;
    const bool Enabled=P.bCrewAlive && P.Attackers>0 && P.Defenders==0;
    const auto& State=SiegeState()->Siege;
    const FVector Destination=Battlefield->EquipmentDestination(State.Objective);
    if (Enabled)
    {
        const float Speed=100*WarSiege::ParticipationRate(P.Attackers,true);
        // Keep the support engine behind the ram; both use real navigation and hull sweeps.
        const FVector Follow=Convoy[0]->TrailingLocation(850);
        Convoy[1]->Drive(Follow,Speed*1.15f,Delta);
        if (FVector::Dist2D(Convoy[0]->GetActorLocation(),Convoy[1]->GetActorLocation())<1200)
            Convoy[0]->Drive(Destination,Speed,Delta);
        else Convoy[0]->Stop();
    }
    else for (const auto& Vehicle:Convoy) Vehicle->Stop();
    Convoy[0]->Operate(Enabled && State.Objective==3 && FVector::Dist2D(Convoy[0]->GetActorLocation(),Destination)<5);
}
