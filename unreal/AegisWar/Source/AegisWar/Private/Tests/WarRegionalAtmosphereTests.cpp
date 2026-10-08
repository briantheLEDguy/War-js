#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarRegionalAtmosphere.h"
#include "Engine/World.h"
#include "Components/AudioComponent.h"
#include "ProceduralMeshComponent.h"
#include "Materials/Material.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarRegionalAtmosphereTest,"AegisWar.Foundation.RegionalAtmosphere",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarRegionalAtmosphereTest::RunTest(const FString& Parameters)
{
    using namespace WarRegionalAtmosphere;
    const auto Day=Mix(1,1,1,.8f,false,false),Night=Mix(1,1,0,.8f,false,false),Inside=Mix(1,1,1,.8f,true,false);
    TestTrue(TEXT("Village work quietens at night"),Night.Work<Day.Work*.2f);
    TestTrue(TEXT("Indoor nature and weather attenuate"),Inside.Nature<Day.Nature*.2f&&Inside.Weather<Day.Weather*.2f);
    TestTrue(TEXT("Military pressure responds to local combat"),Mix(0,1,1,0,false,true).Military>Day.Military);
    TestEqual(TEXT("Outside village work is absent"),Mix(0,0,1,0,false,false).Work,0.f);
    const float NaN=std::numeric_limits<float>::quiet_NaN();
    TestEqual(TEXT("Invalid weather is silent"),Mix(0,0,1,NaN,false,false).Weather,0.f);
    TestTrue(TEXT("Capital has no local sample bed"),Samples(TEXT("aegis_capital"),0,50,Day).IsEmpty());
    TestTrue(TEXT("Negative sample offset rejected"),Samples(TEXT("sunmeadow_march"),-1,50,Day).IsEmpty());
    TestTrue(TEXT("Unbounded sample allocation rejected"),Samples(TEXT("sunmeadow_march"),0,SampleRate*13,Day).IsEmpty());
    TestTrue(TEXT("Overflow rejected"),Samples(TEXT("sunmeadow_march"),MAX_int64-2,50,Day).IsEmpty());
    const auto Whole=Samples(TEXT("sunmeadow_march"),0,1000,Day);
    auto Chunks=Samples(TEXT("sunmeadow_march"),0,357,Day);Chunks.Append(Samples(TEXT("sunmeadow_march"),357,643,Day));
    TestTrue(TEXT("Chunk boundaries preserve synthesized signal"),Whole==Chunks);
    TestTrue(TEXT("Distinct region has distinct signal"),Whole!=Samples(TEXT("cinderfen_outskirts"),0,1000,Day));
    TestTrue(TEXT("Zero gains mute all voices"),Samples(TEXT("sunmeadow_march"),0,100,{}).ContainsByPredicate([](int16 P){return P!=0;})==false);
    const auto Loud=Samples(TEXT("cinderfen_outskirts"),0,10000,{100,100,100,100});
    TestFalse(TEXT("Bounded synthesized output avoids clipping"),Loud.ContainsByPredicate([](int16 P){return FMath::Abs(int32(P))>19661;}));
    TestEqual(TEXT("Rain budget capped"),ParticleCount(TEXT("sunmeadow_march"),10,false),MaximumParticles);
    TestEqual(TEXT("Steam budget bounded"),ParticleCount(TEXT("cinderfen_outskirts"),1,false),24);
    TestEqual(TEXT("Ash budget bounded"),ParticleCount(TEXT("ashen_steppe"),1,false),96);
    TestEqual(TEXT("Indoor particles absent"),ParticleCount(TEXT("sunmeadow_march"),1,true),0);
    TestEqual(TEXT("Capital particles absent"),ParticleCount(TEXT("aegis_capital"),1,false),0);
    const auto Wav=AWarRegionalAtmosphere::AudioStudy(TEXT("sunmeadow_march"),1,0,1,.8f,false);
    TestEqual(TEXT("Eight second mono study bounded"),Wav.Num(),44+8*SampleRate*2);
    TestTrue(TEXT("PCM WAV header"),Wav.Num()>44&&Wav[0]=='R'&&Wav[8]=='W'&&Wav[20]==1&&Wav[22]==1&&Wav[34]==16);
    TestTrue(TEXT("Unknown zone has no WAV"),AWarRegionalAtmosphere::AudioStudy(TEXT("missing"),0,0,1,0,false).IsEmpty());
    const auto Values=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Values);
    if(!TestNotNull(TEXT("Preview world"),World))return false;
    auto* Actor=World->SpawnActor<AWarRegionalAtmosphere>();Actor->ZoneId=TEXT("sunmeadow_march");
    TestFalse(TEXT("Effects never replicate"),Actor->GetIsReplicated());
    TestEqual(TEXT("Weather never blocks movement"),Actor->WeatherMesh->GetCollisionEnabled(),ECollisionEnabled::NoCollision);
    TestFalse(TEXT("Weather never changes navigation"),Actor->WeatherMesh->CanEverAffectNavigation());
    TestFalse(TEXT("Audio does not autoplay"),Actor->Audio->bAutoActivate);
    Actor->WeatherMaterial=NewObject<UMaterial>(Actor);
    TestTrue(TEXT("Editor weather preview"),Actor->PreviewFrame(FVector::ZeroVector,FVector::ForwardVector,1200,.8f,false));
    TestEqual(TEXT("Preview renders admitted rain budget"),Actor->GetParticleCount(),154);
    TestTrue(TEXT("Sheltered preview"),Actor->PreviewFrame(FVector::ZeroVector,FVector::ForwardVector,1200,.8f,true));
    TestEqual(TEXT("Shelter clears weather geometry"),Actor->GetParticleCount(),0);
    TestFalse(TEXT("Invalid preview rejected"),Actor->PreviewFrame(FVector::ZeroVector,FVector::ForwardVector,NaN,.8f,false));
    Actor->ZoneId=TEXT("aegis_capital");
    TestFalse(TEXT("Capital preview rejected"),Actor->PreviewFrame(FVector::ZeroVector,FVector::ForwardVector,1200,.8f,false));
    World->DestroyWorld(false);return true;
}
#endif
