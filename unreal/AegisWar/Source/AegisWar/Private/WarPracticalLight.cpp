#include "WarPracticalLight.h"
#include "WarEnvironmentState.h"
#include "Components/PointLightComponent.h"
#include "Engine/World.h"

AWarPracticalLight::AWarPracticalLight()
{
    SetReplicates(false);
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=.5f;
    auto* Light=CastChecked<UPointLightComponent>(GetLightComponent());
    Light->SetMobility(EComponentMobility::Movable);
    Light->SetIntensityUnits(ELightUnits::Lumens);
    Light->SetIntensity(0);
    Light->SetAttenuationRadius(1400);
    Light->SetLightColor(FLinearColor(FColor(255,190,105)));
    // The fixture supplies local orientation cues; broad terrain lights supply silhouettes.
    Light->SetCastShadows(false);
}
void AWarPracticalLight::ApplyTime(double Seconds)
{
    const float Day=AWarEnvironmentState::Daylight(Seconds);
    GetLightComponent()->SetIntensity(FMath::Clamp(NightLumens,0.f,5000.f)*(1-Day)*(1-Day));
}
void AWarPracticalLight::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(GetWorld()->GetNetMode()==NM_DedicatedServer||!AWarEnvironmentState::IsDynamicZone(ZoneId))return;
    const auto* State=AWarEnvironmentState::Find(GetWorld());
    if(State&&State->UnixSeconds()>=0)ApplyTime(State->UnixSeconds());
}
