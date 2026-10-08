#include "WarRegionalAtmosphere.h"
#include "WarEnvironmentState.h"

namespace
{
float Unit(float Value) { return FMath::IsFinite(Value) ? FMath::Clamp(Value,0.f,1.f) : 0; }
float Noise(int64 Sample,uint32 Salt)
{
    uint32 Hash=uint32(Sample)^Salt;Hash^=Hash>>16;Hash*=0x7feb352du;Hash^=Hash>>15;Hash*=0x846ca68bu;Hash^=Hash>>16;
    return (Hash&0xffff)/32767.5f-1;
}
float Pulse(double Time,double Period,double Decay)
{ return FMath::Exp(-FMath::Fmod(Time,Period)*Decay); }
}

FWarAtmosphereMix WarRegionalAtmosphere::Mix(float Village,float Frontage,float Day,float Weather,bool bInside,bool bCombat)
{
    Village=Unit(Village);Frontage=Unit(Frontage);Day=Unit(Day);Weather=Unit(Weather);
    const float Shelter=bInside ? .18f : 1.f;
    return {.10f*(1-Village*.6f)*Shelter,.13f*Weather*Shelter,
        .16f*Village*(.12f+.88f*Day)*(bInside ? .35f : 1.f),
        .08f*Frontage*(bCombat ? 1.f : .3f)*(bInside ? .3f : 1.f)};
}

int32 WarRegionalAtmosphere::ParticleCount(FName Zone,float Strength,bool bInside)
{
    if(bInside||!AWarEnvironmentState::IsDynamicZone(Zone))return 0;
    Strength=Unit(Strength);
    if(Zone==TEXT("cinderfen_outskirts"))return FMath::RoundToInt(8+Strength*16);
    if(Zone==TEXT("ashen_steppe"))return FMath::RoundToInt(12+Strength*84);
    return FMath::Clamp(FMath::RoundToInt(Strength*MaximumParticles),0,MaximumParticles);
}

TArray<int16> WarRegionalAtmosphere::Samples(FName Zone,int64 First,int32 Count,const FWarAtmosphereMix& In)
{
    if(!AWarEnvironmentState::IsDynamicZone(Zone)||First<0||Count<1||Count>SampleRate*12||First>MAX_int64-Count)return {};
    TArray<int16> Result;Result.SetNumUninitialized(Count);
    const float Nature=Unit(In.Nature),Weather=Unit(In.Weather),Work=Unit(In.Work),Military=Unit(In.Military);
    const bool Steam=Zone==TEXT("cinderfen_outskirts"),Ash=Zone==TEXT("ashen_steppe"),Fen=Zone==TEXT("brightfen_approach");
    for(int32 I=0;I<Count;++I)
    {
        const int64 Index=First+I;const double T=double(Index)/SampleRate;
        // Slow noise knots interpolate continuously across queued chunks; fine noise adds rain/steam detail.
        const int64 Knot=Index/120;const float F=float(Index%120)/120;
        const float Wind=FMath::Lerp(Noise(Knot,71),Noise(Knot+1,71),F);
        const float Hiss=Noise(Index,Steam ? 971 : 313);
        const float Gust=.45f+.35f*FMath::Sin(T*.37)+.2f*FMath::Sin(T*.13);
        const float Chirp=FMath::Sin(2*PI*(Fen ? 1250 : 1950)*T)*Pulse(T,3.7,.9)*.25f;
        const float NatureSound=Wind*Gust+(Steam||Ash ? 0 : Chirp);
        const float WeatherSound=Steam ? Hiss*.25f+Wind*.65f : Ash ? Wind*.8f : Hiss*.48f+Wind*.3f;
        const float Strike=Pulse(T,Steam ? 1.67 : 2.13,24)*FMath::Sin(2*PI*(Steam ? 640 : 430)*T);
        const float WorkSound=Strike*.55f+Pulse(T,4.83,5)*Wind*.25f;
        const float Drum=Pulse(T,2.91,13)*FMath::Sin(2*PI*83*T);
        const float Sample=NatureSound*Nature+WeatherSound*Weather+WorkSound*Work+Drum*Military;
        Result[I]=int16(FMath::Clamp(Sample,-.6f,.6f)*32767);
    }
    return Result;
}
