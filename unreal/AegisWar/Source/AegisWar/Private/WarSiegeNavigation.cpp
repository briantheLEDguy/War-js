#include "WarSiegeNavigation.h"
#include "GameFramework/Character.h"
#include "Components/CapsuleComponent.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "NavigationData.h"
#include "EngineUtils.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeBattlefield.h"
#include "WarCitadelNavigationFilter.h"
#include "GameFramework/Controller.h"

TSubclassOf<UNavigationQueryFilter> WarSiegeNavigation::FilterFor(const AActor* Actor)
{
    const auto* State=Cast<AWarPlayerState>(Actor);
    if (const auto* Pawn=Cast<AWarCharacter>(Actor)) State=Pawn->GetPlayerState<AWarPlayerState>();
    else if (const auto* Controller=Cast<AController>(Actor)) State=Controller->GetPlayerState<AWarPlayerState>();
    const auto* Encounter=State ? State->GetSiegeEncounter() : nullptr;
    return Encounter && Encounter->Owns(State) && Encounter->Siege.RulesVersion==2
        && Encounter->Battlefield && Encounter->Battlefield->DefinitionVersion==2
        ? UWarCitadelNavigationFilter::StaticClass() : nullptr;
}

bool WarSiegeNavigation::Detour(const ACharacter* Pawn,const FVector& Goal,float Side,FVector& Ground)
{
    if (!IsValid(Pawn) || Goal.ContainsNaN() || !FMath::IsFinite(Side)) return false;
    const FVector Toward=(Goal-Pawn->GetActorLocation()).GetSafeNormal2D();
    return Approach(Pawn,Pawn->GetActorLocation(),FVector(-Toward.Y,Toward.X,0)*400*(Side>=0 ? 1 : -1),900,Ground);
}

bool WarSiegeNavigation::SpawnCandidate(UWorld* World,const FVector& Ground,float Radius,float HalfHeight,FVector& Center,const AActor* Ignore)
{
    if (!World || Ground.ContainsNaN() || !FMath::IsFinite(Radius) || !FMath::IsFinite(HalfHeight) || Radius<=0 || HalfHeight<Radius) return false;
    FHitResult Floor; FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeSpawn),false);
    if (Ignore) Query.AddIgnoredActor(Ignore);
    // A standing participant must not be mistaken for the walkable floor.
    if (!World->LineTraceSingleByObjectType(Floor,Ground+FVector(0,0,100),Ground-FVector(0,0,100),
        FCollisionObjectQueryParams(ECC_WorldStatic),Query) || Floor.ImpactNormal.Z<.7f
        || FMath::Abs(Floor.ImpactPoint.Z-Ground.Z)>25) return false;
    const FVector Candidate=Floor.ImpactPoint+FVector(0,0,HalfHeight-Radius+Radius/Floor.ImpactNormal.Z+3);
    if (World->OverlapBlockingTestByChannel(Candidate,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(Radius,HalfHeight),Query)) return false;
    Center=Candidate; return true;
}
bool WarSiegeNavigation::SpawnCenter(UWorld* World,const FVector& Anchor,FVector& Center,const ACharacter* Avatar)
{
    auto* Nav=World ? FNavigationSystem::GetCurrent<UNavigationSystemV1>(World) : nullptr;
    if (!Nav || Anchor.ContainsNaN()) return false;
    const auto* Character=Avatar ? Avatar : GetDefault<AWarCharacter>();
    const auto* Capsule=Character->GetCapsuleComponent();
    const auto* Data=Nav->GetNavDataForProps(Character->GetNavAgentPropertiesRef());
    if (!Data) return false;
    for (float Ring:{0.f,150.f,300.f,450.f,600.f}) for (int32 I=0;I<(Ring==0 ? 1 : 12);++I)
    {
        const float Angle=I*PI/6;
        FNavLocation Ground; FVector Candidate;
        if (Nav->ProjectPointToNavigation(Anchor+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*Ring,Ground,FVector(60,60,500),Data)
            && SpawnCandidate(World,Ground.Location,Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight(),Candidate,Avatar)
            && FVector::DistSquared(Anchor,Candidate)<FMath::Square(700.f))
        { Center=Candidate; return true; }
    }
    return false;
}

bool WarSiegeNavigation::Approach(const ACharacter* Pawn,const FVector& Anchor,const FVector& PreferredOffset,float CaptureRadius,FVector& Ground)
{
    if (!IsValid(Pawn) || Anchor.ContainsNaN() || PreferredOffset.ContainsNaN() || !FMath::IsFinite(CaptureRadius) || CaptureRadius<200) return false;
    auto* World=Pawn->GetWorld(); auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Nav) return false;
    const auto* Data=Nav->GetNavDataForProps(Pawn->GetNavAgentPropertiesRef());
    if (!Data) return false;
    const auto* Capsule=Pawn->GetCapsuleComponent();
    const float Radius=Capsule->GetScaledCapsuleRadius(), Half=Capsule->GetScaledCapsuleHalfHeight();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SiegeApproach),false,Pawn);
    // Crowd avoidance handles moving characters. Static props must be excluded
    // by physical capsule clearance even if their navmesh projection succeeds.
    for (TActorIterator<APawn> It(World);It;++It) Query.AddIgnoredActor(*It);
    const float StartAngle=FMath::Atan2(PreferredOffset.Y,PreferredOffset.X);
    const float Reach=CaptureRadius-100, Outer=FMath::Min(450.f,Reach-60);
    for (float Ring:{FMath::Clamp(float(PreferredOffset.Size2D()),20.f,Outer),Outer*.55f,Outer}) for (int32 Attempt=0;Attempt<8;++Attempt)
    {
        const float Angle=StartAngle+Attempt*PI/4;
        const FVector Seed=Anchor+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*Ring;
        FNavLocation Projected;
        if (!Nav->ProjectPointToNavigation(Seed,Projected,FVector(60,60,180),Data) || FVector::Dist2D(Anchor,Projected.Location)>Reach) continue;
        FHitResult Floor;
        if (!World->LineTraceSingleByChannel(Floor,Projected.Location+FVector(0,0,100),Projected.Location-FVector(0,0,100),ECC_Visibility,Query)
            || Floor.ImpactNormal.Z<.7 || FMath::Abs(Floor.ImpactPoint.Z-Projected.Location.Z)>25) continue;
        // A capsule resting on an incline sits above its centre floor sample;
        // account for its rounded base before testing walls and nearby props.
        const float FloorClearance=Half-Radius+Radius/Floor.ImpactNormal.Z+3;
        const FVector Center=Floor.ImpactPoint+FVector(0,0,FloorClearance);
        if (World->OverlapBlockingTestByChannel(Center,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(Radius,Half-1),Query)) continue;
        auto* Path=UNavigationSystemV1::FindPathToLocationSynchronously(World,Pawn->GetActorLocation(),Projected.Location,
            const_cast<ACharacter*>(Pawn),FilterFor(Pawn));
        if (!Path || !Path->IsValid() || Path->IsPartial()) continue;
        Ground=Projected.Location; return true;
    }
    return false;
}
