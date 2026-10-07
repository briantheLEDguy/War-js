#include "WarEnvironmentState.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

namespace
{
    const TArray<FName> Zones = {TEXT("sunmeadow_march"),TEXT("brightfen_approach"),TEXT("cinderfen_outskirts"),TEXT("ashen_steppe")};
    float Smooth(float T) { T=FMath::Clamp(T,0.f,1.f);return T*T*(3-2*T); }
}
AWarEnvironmentState::AWarEnvironmentState()
{
    bReplicates=true;bAlwaysRelevant=true;bNetLoadOnClient=false;
    SetNetUpdateFrequency(1);PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickInterval=1;
    SetReplicateMovement(false);
}
void AWarEnvironmentState::BeginPlay()
{
    Super::BeginPlay();
    if (HasAuthority())
    {
        const auto Now=FDateTime::UtcNow();
        AnchorUnixSeconds=double(Now.ToUnixTimestamp())+Now.GetMillisecond()/1000.;
        AnchorServerSeconds=GetWorld()->GetGameState() ? GetWorld()->GetGameState()->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
        Tick(0);ForceNetUpdate();
    }
    else SetActorTickEnabled(false);
}
void AWarEnvironmentState::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarEnvironmentState,AnchorUnixSeconds);
    DOREPLIFETIME(AWarEnvironmentState,AnchorServerSeconds);
    DOREPLIFETIME(AWarEnvironmentState,Regions);
}
double AWarEnvironmentState::UnixSeconds() const
{
    const auto* State=GetWorld() ? GetWorld()->GetGameState() : nullptr;
    if (!State || !FMath::IsFinite(AnchorUnixSeconds) || AnchorUnixSeconds<=0 || !FMath::IsFinite(AnchorServerSeconds)) return -1;
    return AnchorUnixSeconds+State->GetServerWorldTimeSeconds()-AnchorServerSeconds;
}
bool AWarEnvironmentState::IsDynamicZone(FName Zone) { return Zones.Contains(Zone); }
double AWarEnvironmentState::CycleSeconds(double Seconds)
{
    if (!FMath::IsFinite(Seconds)) return 0;
    const double Value=FMath::Fmod(Seconds,3600.);return Value<0 ? Value+3600 : Value;
}
float AWarEnvironmentState::Daylight(double Seconds)
{
    const double Phase=CycleSeconds(Seconds);
    if (Phase<300) return Smooth(Phase/300);
    if (Phase<2100) return 1;
    if (Phase<2400) return 1-Smooth((Phase-2100)/300);
    return 0;
}
float AWarEnvironmentState::WeatherAt(FName Zone,int64 Interval)
{
    if (!IsDynamicZone(Zone)) return 0;
    // Stable server selection retains regional weather through restart without a client RNG or extra persistence schema.
    uint32 Hash=2166136261u;
    for (TCHAR Character:Zone.ToString()) Hash=(Hash^uint32(Character))*16777619u;
    Hash=(Hash^uint32(Interval))*16777619u;Hash=(Hash^uint32(uint64(Interval)>>32))*16777619u;
    const uint32 Choice=Hash%10;
    return Choice==0 ? .8f : Choice<4 ? .28f : .06f;
}
void AWarEnvironmentState::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const double Now=UnixSeconds();
    if (!HasAuthority() || Now<0) return;
    const int64 Interval=FMath::FloorToInt64(Now/600.);
    if (Interval==LastWeatherInterval) return;
    LastWeatherInterval=Interval;Regions.Reset();
    for (FName Zone:Zones)
    {
        FWarRegionalWeather Row;Row.Zone=Zone;
        Row.Kind=Zone==TEXT("ashen_steppe") ? TEXT("ash") : Zone==TEXT("cinderfen_outskirts") ? TEXT("steam") : TEXT("rain");
        Row.FromStrength=FMath::Min(WeatherAt(Zone,Interval-1),.28f);Row.Strength=WeatherAt(Zone,Interval);Row.TransitionUnixSeconds=Interval*600.;
        Regions.Add(Row);
    }
    ForceNetUpdate();
}
float AWarEnvironmentState::WeatherStrength(FName Zone) const
{
    const double Now=UnixSeconds();if (Now<0) return 0;
    const auto* Row=Regions.FindByPredicate([Zone](const auto& Value){return Value.Zone==Zone;});
    if (!Row || !FMath::IsFinite(Row->Strength) || !FMath::IsFinite(Row->FromStrength)
        || !FMath::IsFinite(Row->TransitionUnixSeconds)) return 0;
    const float T=Smooth((Now-Row->TransitionUnixSeconds)/45.);
    float Strength=FMath::Lerp(FMath::Clamp(Row->FromStrength,0.f,1.f),FMath::Clamp(Row->Strength,0.f,1.f),T);
    // Strong spells ease back after three minutes; the remaining interval stays mild.
    if (Row->Strength>.5f) Strength=FMath::Lerp(Strength,.28f,Smooth((Now-Row->TransitionUnixSeconds-180)/45.));
    return Strength;
}
AWarEnvironmentState* AWarEnvironmentState::Find(UWorld* World)
{
    if (!World) return nullptr;AWarEnvironmentState* Result=nullptr;
    for (TActorIterator<AWarEnvironmentState> It(World);It;++It)
    { if (Result) return nullptr;Result=*It; }
    return Result;
}
bool UWarEnvironmentSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{ return Type==EWorldType::Game || Type==EWorldType::PIE || Type==EWorldType::GamePreview; }
void UWarEnvironmentSubsystem::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    if (World.GetNetMode()==NM_Client || AWarEnvironmentState::Find(&World)) return;
    for (TActorIterator<AWarEnvironmentState> It(&World);It;++It) return;
    FActorSpawnParameters Parameters;Parameters.ObjectFlags|=RF_Transient;
    Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    World.SpawnActor<AWarEnvironmentState>(Parameters);
}
