#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCombatFeedback.h"
#include "WarImpactCameraModifier.h"
#include "WarPlayerController.h"
#include "Camera/CameraTypes.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "Serialization/MemoryWriter.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCombatFeedbackTest, "AegisWar.Foundation.CombatFeedback",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCombatFeedbackTest::RunTest(const FString& Parameters)
{
    TArray<FWarCombatNotice> Notices; uint32 Serial = 0;
    TestTrue(TEXT("Confirmed effective healing displayed"), WarCombatFeedback::Append(Notices, Serial, 1, TEXT("Heal"), TEXT("Ally"), 25, 10));
    TestFalse(TEXT("Duplicate cannot display twice"), WarCombatFeedback::Append(Notices, Serial, 1, TEXT("Heal"), TEXT("Ally"), 25, 10));
    TestFalse(TEXT("Overheal has no effective-heal message"), WarCombatFeedback::Append(Notices, Serial, 2, TEXT("Heal"), TEXT("Ally"), 0, 10));
    TestFalse(TEXT("Invented event kinds rejected"), WarCombatFeedback::Append(Notices, Serial, 2, TEXT("Victory"), TEXT("Ally"), 1, 10));
    TestFalse(TEXT("Negative damage rejected"), WarCombatFeedback::Append(Notices, Serial, 2, TEXT("Hit"), TEXT("Enemy"), -1, 10));
    TestTrue(TEXT("Interruption needs no damage"), WarCombatFeedback::Append(Notices, Serial, 3, TEXT("Interrupt"), TEXT("Enemy"), 0, 10));
    TestFalse(TEXT("Out-of-order packet cannot revive feedback"), WarCombatFeedback::Append(Notices, Serial, 2, TEXT("Hit"), TEXT("Enemy"), 1, 10));
    for (uint32 I = 4; I < 40; ++I) WarCombatFeedback::Append(Notices, Serial, I, TEXT("Hit"), TEXT("Enemy"), 1, 10);
    TestEqual(TEXT("Bounded on-screen messages"), Notices.Num(), 6);
    WarCombatFeedback::Append(Notices, Serial, 40, TEXT("Guarded"), TEXT("Enemy"), 10, 14);
    TestEqual(TEXT("Expired messages discarded"), Notices.Num(), 1);
    TestTrue(TEXT("Explicit critical outcome has distinct feedback"),WarCombatFeedback::Append(Notices,Serial,41,TEXT("CriticalHit"),TEXT("Enemy"),25,14));
    TestEqual(TEXT("Critical feedback does not multiply the damage amount"),Notices.Last().Amount,25.f);

    const FString Directory=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("CombatFeedbackReview"));
    IFileManager::Get().MakeDirectory(*Directory,true);
    for (bool bCritical:{false,true})
    {
        const auto Samples=WarCombatFeedback::ImpactSamples(42,bCritical);
        TestEqual(TEXT("Impact duration is 180ms"),Samples.Num(),3969);
        int32 Peak=0; double AttackEnergy=0, TailEnergy=0;
        for (int32 I=0;I<Samples.Num();++I)
        {
            Peak=FMath::Max(Peak,FMath::Abs(static_cast<int32>(Samples[I])));
            if (I<1102) AttackEnergy+=FMath::Square(static_cast<double>(Samples[I]));
            if (I>=Samples.Num()-1102) TailEnergy+=FMath::Square(static_cast<double>(Samples[I]));
        }
        TestTrue(TEXT("Audible transient has headroom without clipping"),Peak>5000 && Peak<30000);
        TestTrue(TEXT("Impact tail decays below one percent of attack energy"),TailEnergy<AttackEnergy*.01);
        TestEqual(TEXT("Sound begins without a discontinuity"),Samples[0],static_cast<int16>(0));
        TestTrue(TEXT("Sound ends near silence"),FMath::Abs(static_cast<int32>(Samples.Last()))<100);
        if (FParse::Param(FCommandLine::Get(),TEXT("WarCaptureCombatFeedback")))
        {
            TArray<uint8> Wave; FMemoryWriter Writer(Wave);
            const auto Tag=[&](const ANSICHAR* Text) { Writer.Serialize(const_cast<ANSICHAR*>(Text),4); };
            uint32 DataBytes=Samples.Num()*sizeof(int16), RiffBytes=DataBytes+36, FormatBytes=16;
            uint16 PCM=1, Channels=1, BlockAlign=2, Bits=16;
            uint32 Rate=WarCombatFeedback::ImpactSampleRate, BytesPerSecond=Rate*BlockAlign;
            Tag("RIFF"); Writer<<RiffBytes; Tag("WAVE"); Tag("fmt "); Writer<<FormatBytes<<PCM<<Channels<<Rate<<BytesPerSecond<<BlockAlign<<Bits;
            Tag("data"); Writer<<DataBytes; Writer.Serialize(const_cast<int16*>(Samples.GetData()),DataBytes);
            TestTrue(TEXT("Production impact audio exported"),FFileHelper::SaveArrayToFile(Wave,*FPaths::Combine(Directory,bCritical ? TEXT("critical.wav") : TEXT("normal.wav"))));
        }
    }
    TestTrue(TEXT("Critical impact has distinct samples"),WarCombatFeedback::ImpactSamples(42,false)!=WarCombatFeedback::ImpactSamples(42,true));

    auto* Modifier=NewObject<UWarImpactCameraModifier>();
    const auto Measure=[&](float Intensity) {
        Modifier->Pulse(Intensity); double Peak=0;
        for (int32 Frame=0;Frame<24;++Frame)
        {
            FMinimalViewInfo View; View.Location=FVector(10,20,30); View.Rotation=FRotator::ZeroRotator; View.FOV=90;
            Modifier->ModifyCamera(1.f/120,View);
            Peak=FMath::Max(Peak,FMath::Abs(View.Rotation.Pitch)+FMath::Abs(View.Rotation.Roll));
            TestEqual(TEXT("Camera impulse preserves view location"),View.Location,FVector(10,20,30));
            TestEqual(TEXT("Camera impulse preserves FOV"),View.FOV,90.f);
            if (Frame==23) TestTrue(TEXT("Camera settles after the impulse"),View.Rotation.IsZero());
        }
        return Peak;
    };
    TestEqual(TEXT("Off produces no camera motion"),Measure(0),0.);
    const double Light=Measure(.25f), Full=Measure(1);
    TestTrue(TEXT("Light is visible but smaller than full intensity"),Light>0 && FMath::IsNearlyEqual(Light*4,Full,.0001));
    Modifier->Pulse(1); Modifier->Stop(); FMinimalViewInfo Stopped;
    Modifier->ModifyCamera(1.f/60,Stopped); TestTrue(TEXT("Turning off stops a running impulse immediately"),Stopped.Rotation.IsZero());

    // Keep persistence testing away from the user's real preferences.
    TGuardValue<FString> SettingsFile(GGameUserSettingsIni,FPaths::Combine(Directory,TEXT("test-settings.ini")));
    // SetFloat only writes registered config branches; production registers
    // GameUserSettings at startup, so the isolated test must do the same.
    GConfig->Add(GGameUserSettingsIni,FConfigFile());
    auto* Instance=NewObject<UGameInstance>(GEngine); Instance->AddToRoot(); Instance->InitializeStandalone();
    auto* World=Instance->GetWorld();
    auto* Controller=World->SpawnActor<AWarPlayerController>();
    TestEqual(TEXT("New combat shake defaults to light"),Controller->GetCombatShakeIntensity(),.25f);
    Controller->SetControlRotation(FRotator(10,35,0));
    Controller->SetCombatShakeIntensity(0); Controller->SaveInterfacePreferences();
    FConfigFile DiskSettings; DiskSettings.Read(GGameUserSettingsIni);
    float Saved=-1; DiskSettings.GetFloat(TEXT("AegisWar.Interface"),TEXT("CombatShakeIntensity"),Saved);
    TestEqual(TEXT("Off preference persists"),Saved,0.f);
    TestEqual(TEXT("Changing shake preserves aiming rotation"),Controller->GetControlRotation(),FRotator(10,35,0));
    Controller->SetCombatShakeIntensity(2); TestEqual(TEXT("Shake setting clamps to full"),Controller->GetCombatShakeIntensity(),1.f);
    Controller->SetCombatShakeIntensity(-1); TestEqual(TEXT("Negative shake setting clamps to off"),Controller->GetCombatShakeIntensity(),0.f);
    Instance->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); Instance->RemoveFromRoot();
    GConfig->Remove(GGameUserSettingsIni);
    return true;
}
#endif
