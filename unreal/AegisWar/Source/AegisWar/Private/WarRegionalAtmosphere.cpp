#include "WarRegionalAtmosphere.h"
#include "WarEnvironmentState.h"
#include "WarZoneAnchor.h"
#include "WarInteriorAtmosphere.h"
#include "WarPlayerController.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "ProceduralMeshComponent.h"
#include "Sound/SoundWaveProcedural.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

AWarRegionalAtmosphere::AWarRegionalAtmosphere()
{
    SetReplicates(false);SetCanBeDamaged(false);
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickInterval=.05f;
    WeatherMesh=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("LocalWeather"));SetRootComponent(WeatherMesh);
    WeatherMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);WeatherMesh->SetGenerateOverlapEvents(false);
    WeatherMesh->SetCanEverAffectNavigation(false);WeatherMesh->SetCastShadow(false);
    WeatherMesh->ComponentTags.Add(TEXT("WarIntentionalEffect"));
    Audio=CreateDefaultSubobject<UAudioComponent>(TEXT("RegionalSoundBed"));Audio->SetupAttachment(WeatherMesh);
    Audio->bAutoActivate=false;Audio->bAllowSpatialization=false;Audio->bIsUISound=false;
    Tags.Add(TEXT("WarLocalRegionalAtmosphere"));
}
void AWarRegionalAtmosphere::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer||!AWarEnvironmentState::IsDynamicZone(ZoneId))SetActorTickEnabled(false);
}
bool AWarRegionalAtmosphere::InsideRoom(FVector Eye) const
{
    for(TActorIterator<AWarInteriorAtmosphere> It(GetWorld());It;++It)
    {
        if(It->ZoneId!=ZoneId)continue;
        const FVector P=It->RoomBounds->GetComponentTransform().InverseTransformPosition(Eye);
        const FVector E=It->RoomBounds->GetUnscaledBoxExtent();
        if(FMath::Abs(P.X)<=E.X&&FMath::Abs(P.Y)<=E.Y&&FMath::Abs(P.Z)<=E.Z)return true;
    }
    // Other retained roofed buildings also shelter the observer; effect geometry has no query collision.
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(RegionalRoof),false,this);
    return GetWorld()->LineTraceSingleByChannel(Hit,Eye+FVector(0,0,10),Eye+FVector(0,0,650),ECC_Visibility,Query);
}
void AWarRegionalAtmosphere::StopLocalEffects()
{
    WeatherMesh->ClearAllMeshSections();VisibleParticles=0;bActive=false;CurrentMix={};
    if(Audio->IsPlaying())Audio->Stop();
    if(Wave)Wave->ResetAudio();
}
void AWarRegionalAtmosphere::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!GetWorld()->IsGameWorld()||GetNetMode()==NM_DedicatedServer)return;
    AWarPlayerController* Player=nullptr;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* P=Cast<AWarPlayerController>(It->Get());P&&P->IsLocalController()&&P->GetPawn()){Player=P;break;}
    const auto* Anchor=Player ? AWarZoneAnchor::FindAt(GetWorld(),Player->GetPawn()->GetActorLocation()) : nullptr;
    const auto* Clock=AWarEnvironmentState::Find(GetWorld());
    if(!Player||!Anchor||Anchor->ZoneId!=ZoneId||!Clock||Clock->UnixSeconds()<0)
    {if(bActive)StopLocalEffects();return;}
    const double Now=Clock->UnixSeconds();
    const FVector Eye=Player->PlayerCameraManager ? Player->PlayerCameraManager->GetCameraLocation() : Player->GetPawn()->GetActorLocation();
    const FVector Forward=Player->PlayerCameraManager ? Player->PlayerCameraManager->GetCameraRotation().Vector() : Player->GetControlRotation().Vector();
    bObserverInside=InsideRoom(Eye);bActive=true;
    const FVector Local=GetActorTransform().InverseTransformPosition(Player->GetPawn()->GetActorLocation());
    const float Village=1-FMath::Clamp(float(FVector::Dist2D(Local,VillageCentre)-12000)/23000,0.f,1.f);
    float Frontage=0;
    for(const auto& Centre:MilitaryCentres)if(!Centre.ContainsNaN())Frontage=FMath::Max(Frontage,1-float(FMath::Min(FVector::Dist2D(Local,Centre)/24000,1.)));
    const bool Combat=Player->GetCombatNotices().ContainsByPredicate([this](const auto& Notice){return Notice.Expires>GetWorld()->GetTimeSeconds();});
    const auto Target=WarRegionalAtmosphere::Mix(Village,Frontage,AWarEnvironmentState::Daylight(Now),Clock->WeatherStrength(ZoneId),bObserverInside,Combat);
    const float Blend=1-FMath::Exp(-FMath::Max(DeltaSeconds,0.f)/2.f);
    CurrentMix.Nature=FMath::Lerp(CurrentMix.Nature,Target.Nature,Blend);CurrentMix.Weather=FMath::Lerp(CurrentMix.Weather,Target.Weather,Blend);
    CurrentMix.Work=FMath::Lerp(CurrentMix.Work,Target.Work,Blend);CurrentMix.Military=FMath::Lerp(CurrentMix.Military,Target.Military,Blend);
    DrawWeather(Eye,Forward,Now,Clock->WeatherStrength(ZoneId),bObserverInside);
    if(Player->GetInterfaceVolume()<=0||!FMath::IsFinite(AudioGain)||AudioGain<=0){if(Audio->IsPlaying())Audio->Stop();if(Wave)Wave->ResetAudio();return;}
    if(!Wave)
    {
        Wave=NewObject<USoundWaveProcedural>(this);Wave->SetSampleRate(WarRegionalAtmosphere::SampleRate);
        Wave->NumChannels=1;Wave->Duration=INDEFINITELY_LOOPING_DURATION;Wave->bLooping=false;
        Audio->SetSound(Wave);
    }
    // At most half a second queued; no audio-thread callback touches the world or its actor state.
    if(Wave->GetAvailableAudioByteCount()<WarRegionalAtmosphere::SampleRate/2)
    {
        const auto Samples=WarRegionalAtmosphere::Samples(ZoneId,AudioSample,WarRegionalAtmosphere::SampleRate/4,CurrentMix);
        AudioSample+=Samples.Num();Wave->QueueAudio(reinterpret_cast<const uint8*>(Samples.GetData()),Samples.Num()*sizeof(int16));
    }
    Audio->SetVolumeMultiplier(FMath::Clamp(AudioGain,0.f,1.f));
    if(!Audio->IsPlaying())Audio->Play();
}
void AWarRegionalAtmosphere::DrawWeather(FVector Eye,FVector Forward,double Seconds,float Strength,bool bInside)
{
    Strength=FMath::IsFinite(Strength) ? FMath::Clamp(Strength,0.f,1.f) : 0;
    RenderedStrength=Strength;VisibleParticles=WarRegionalAtmosphere::ParticleCount(ZoneId,Strength,bInside);
    if(!WeatherMaterial||VisibleParticles==0){WeatherMesh->ClearAllMeshSections();VisibleParticles=0;return;}
    TArray<FVector> Vertices,Normals;TArray<int32> Indices;TArray<FVector2D> UV;TArray<FLinearColor> Colours;TArray<FProcMeshTangent> Tangents;
    const auto Transform=GetActorTransform();
    FVector Flat(Forward.X,Forward.Y,0);if(!Flat.Normalize())Flat=FVector::ForwardVector;
    const FVector Right=FVector::CrossProduct(FVector::UpVector,Flat);
    const bool Steam=ZoneId==TEXT("cinderfen_outskirts"),Ash=ZoneId==TEXT("ashen_steppe");
    const double Phase=AWarEnvironmentState::CycleSeconds(Seconds);
    for(int32 I=0;I<VisibleParticles;++I)
    {
        const float A=FMath::Frac(I*.61803398875),B=FMath::Frac(I*.754877666),C=FMath::Frac(I*.56984029);
        FVector Centre;float Width,Height,Alpha;
        if(Steam)
        {
            if(SteamSites.IsEmpty()){VisibleParticles=0;break;}
            const FVector Site=Transform.TransformPosition(SteamSites[I%FMath::Min(SteamSites.Num(),16)]);
            const float Rise=FMath::Frac(float(Phase*.08)+C);
            Centre=Site+Right*((A-.5f)*420)+Flat*FMath::Sin(Phase*.13+I)*100+FVector(0,0,80+Rise*500);
            Width=210+Rise*350;Height=150+Rise*300;Alpha=(.035f+.06f*Strength)*FMath::Sin(PI*Rise);
        }
        else
        {
            Centre=Eye+Flat*(450+A*2000)+Right*((B-.5f)*3000);
            const float Fall=FMath::Frac(float(Phase*(Ash ? .07 : .8))+C);
            Centre.Z+=Ash ? (Fall-.5f)*1400 : 800-Fall*1600;
            Centre+=Right*FMath::Sin(Phase*.17+I)*float(Ash ? 220 : 40);
            Width=Ash ? 2+6*A : 2.f;Height=Ash ? Width : 20+20*A;Alpha=Ash ? .18f : .13f+.1f*Strength;
        }
        const FVector Horizontal=Right*Width,Vertical=FVector(Ash ? 0 : -Width*.8,0,Height);
        const FVector Corners[]={Centre-Horizontal-Vertical,Centre+Horizontal-Vertical,Centre+Horizontal+Vertical,Centre-Horizontal+Vertical};
        const FVector2D Tex[]={FVector2D(0,0),FVector2D(1,0),FVector2D(1,1),FVector2D(0,1)};
        const int32 Start=Vertices.Num();const float Light=.4f+.6f*AWarEnvironmentState::Daylight(Seconds);
        for(int32 J=0;J<4;++J){Vertices.Add(Transform.InverseTransformPosition(Corners[J]));Normals.Add(Transform.InverseTransformVectorNoScale(-Flat));UV.Add(Tex[J]);Colours.Add(FLinearColor(.72f*Light,.78f*Light,.8f*Light,Alpha));}
        Indices.Append({Start,Start+1,Start+2,Start,Start+2,Start+3});
    }
    WeatherMesh->CreateMeshSection_LinearColor(0,Vertices,Indices,Normals,UV,Colours,Tangents,false,false);
    WeatherMesh->SetMaterial(0,WeatherMaterial);
}
bool AWarRegionalAtmosphere::PreviewFrame(FVector Eye,FVector Forward,double Seconds,float Strength,bool bInside)
{
    if(GetWorld()->IsGameWorld()||Eye.ContainsNaN()||Forward.ContainsNaN()||!FMath::IsFinite(Seconds)||!FMath::IsFinite(Strength)
        ||!AWarEnvironmentState::IsDynamicZone(ZoneId))return false;
    DrawWeather(Eye,Forward,Seconds,Strength,bInside);return true;
}
FString AWarRegionalAtmosphere::DescribeLocalState() const
{
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("zone"),ZoneId.ToString());Row->SetBoolField(TEXT("active"),bActive);
    Row->SetBoolField(TEXT("observerInside"),bObserverInside);Row->SetNumberField(TEXT("particles"),VisibleParticles);
    Row->SetNumberField(TEXT("strength"),RenderedStrength);Row->SetBoolField(TEXT("replicated"),GetIsReplicated());
    Row->SetBoolField(TEXT("collisionEnabled"),WeatherMesh->GetCollisionEnabled()!=ECollisionEnabled::NoCollision);
    Row->SetBoolField(TEXT("audioPlaying"),Audio->IsPlaying());Row->SetNumberField(TEXT("queuedAudioBytes"),Wave ? Wave->GetAvailableAudioByteCount() : 0);
    FString Result;FJsonSerializer::Serialize(Row,TJsonWriterFactory<>::Create(&Result));return Result;
}
TArray<uint8> AWarRegionalAtmosphere::AudioStudy(FName Zone,float Village,float Frontage,float Day,float Strength,bool bInside)
{
    const auto PCM=WarRegionalAtmosphere::Samples(Zone,0,WarRegionalAtmosphere::SampleRate*8,
        WarRegionalAtmosphere::Mix(Village,Frontage,Day,Strength,bInside,false));
    if(PCM.IsEmpty())return {};
    TArray<uint8> Bytes;Bytes.Reserve(44+PCM.Num()*2);
    const auto Text=[&Bytes](const char* Value){for(int32 I=0;I<4;++I)Bytes.Add(uint8(Value[I]));};
    const auto U16=[&Bytes](uint16 Value){Bytes.Add(uint8(Value));Bytes.Add(uint8(Value>>8));};
    const auto U32=[&Bytes](uint32 Value){for(int32 I=0;I<4;++I)Bytes.Add(uint8(Value>>(I*8)));};
    Text("RIFF");U32(36+PCM.Num()*2);Text("WAVE");Text("fmt ");U32(16);
    U16(1);U16(1);U32(WarRegionalAtmosphere::SampleRate);U32(WarRegionalAtmosphere::SampleRate*2);U16(2);U16(16);
    Text("data");U32(PCM.Num()*2);for(int16 Sample:PCM)U16(uint16(Sample));return Bytes;
}
void AWarRegionalAtmosphere::EndPlay(const EEndPlayReason::Type Reason)
{StopLocalEffects();Super::EndPlay(Reason);}
