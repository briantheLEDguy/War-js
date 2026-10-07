#include "WarInteriorAtmosphere.h"
#include "WarEnvironmentState.h"
#include "Components/BoxComponent.h"
#include "Components/PostProcessComponent.h"
#include "Engine/World.h"

AWarInteriorAtmosphere::AWarInteriorAtmosphere()
{
    SetReplicates(false);
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=.5f;
    RoomBounds=CreateDefaultSubobject<UBoxComponent>(TEXT("RoomBounds"));
    SetRootComponent(RoomBounds);
    RoomBounds->SetBoxExtent(FVector(260,410,140));
    RoomBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RoomBounds->SetGenerateOverlapEvents(false);
    RoomBounds->SetCanEverAffectNavigation(false);
    Exposure=CreateDefaultSubobject<UPostProcessComponent>(TEXT("InteriorExposure"));
    Exposure->SetupAttachment(RoomBounds);
    Exposure->bUnbound=false;
    Exposure->BlendRadius=75;
    Exposure->BlendWeight=1;
    Exposure->Priority=200;
    // Inherit the regional camera/colour settings. Only the room's exposure blends.
    Exposure->Settings.bOverride_AutoExposureBias=true;
    ApplyTime(1200);
}
void AWarInteriorAtmosphere::ApplyTime(double Seconds)
{
    Exposure->Settings.AutoExposureBias=FMath::Lerp(FMath::Clamp(NightExposureBias,-4.f,8.f),
        FMath::Clamp(DayExposureBias,-4.f,8.f),AWarEnvironmentState::Daylight(Seconds));
}
void AWarInteriorAtmosphere::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(GetWorld()->GetNetMode()==NM_DedicatedServer||!AWarEnvironmentState::IsDynamicZone(ZoneId))return;
    const auto* State=AWarEnvironmentState::Find(GetWorld());
    if(State&&State->UnixSeconds()>=0)ApplyTime(State->UnixSeconds());
}
