#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarFloatingCombatText.h"
#include "WarCombatFeedback.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarPlayerState.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarFloatingCombatTextTest, "AegisWar.Foundation.FloatingCombatText",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarFloatingCombatTextTest::RunTest(const FString& Parameters)
{
    const FString TestIni=FPaths::ProjectSavedDir()/TEXT("FloatingCombatTextAutomation.ini");
    TGuardValue<FString> ConfigGuard(GGameUserSettingsIni,TestIni);
    GConfig->Add(TestIni,FConfigFile());
    TArray<FWarFloatingCombatNumber> Numbers;
    const FVector Anchor(10, 20, 200);
    const auto Add = [&](uint32 Id, FName Kind, float Amount, double Now) {
        return WarFloatingCombatText::Add(Numbers, Id, nullptr, Anchor, Kind, Amount, Now);
    };
    TestTrue(TEXT("Confirmed damage accepted without a mapped actor"), Add(1, TEXT("Hit"), 120, 0));
    WarFloatingCombatText::Advance(Numbers, .5);
    TestEqual(TEXT("An isolated hit is halfway through its one-second scroll"), Numbers[0].Progress, .5f);
    TestEqual(TEXT("Missing recipient keeps last known head anchor"), Numbers[0].Anchor, Anchor);
    TestEqual(TEXT("Full opacity before the final fade"), WarFloatingCombatText::Opacity(Numbers[0]), 1.f);
    WarFloatingCombatText::Advance(Numbers, .85);
    TestTrue(TEXT("Final thirty percent fades smoothly"), FMath::IsNearlyEqual(WarFloatingCombatText::Opacity(Numbers[0]), .5f, .0001f));
    WarFloatingCombatText::Advance(Numbers, 1.001);
    TestTrue(TEXT("An isolated hit expires after one second"), Numbers.IsEmpty());
    TestFalse(TEXT("Incoming events are not attributed to the local character"), Add(0, TEXT("Hit"), 12, 2));
    TestFalse(TEXT("Zero effective healing is omitted"), Add(1, TEXT("Heal"), 0, 2));
    TestFalse(TEXT("Guard mitigation is not health damage"), Add(1, TEXT("Guarded"), 12, 2));
    TestFalse(TEXT("Interrupts remain in the combat log"), Add(1, TEXT("Interrupt"), 0, 2));
    TestFalse(TEXT("Negative numbers rejected"), Add(1, TEXT("Hit"), -12, 2));

    Add(2, TEXT("Heal"), 23, 3);
    for (int32 I = 0; I < 20; ++I)
    {
        TestTrue(TEXT("Each of twenty procs in one second is accepted"), Add(1, I % 2 ? TEXT("CriticalHit") : TEXT("Hit"), 17, 3 + I * .05));
        TestTrue(TEXT("Per-recipient burst stays bounded"), Numbers.FilterByPredicate([](const auto& N) { return N.RecipientId == 1; }).Num() <= WarFloatingCombatText::MaxPerRecipient);
        for (const auto& N : Numbers)
        {
            const auto Offset = WarFloatingCombatText::Offset(N);
            TestTrue(TEXT("Horizontal motion and text width fit the overhead region"), FMath::Abs(Offset.X) + WarFloatingCombatText::MaxTextWidth / 2 < WarFloatingCombatText::RegionWidth / 2);
            TestTrue(TEXT("Vertical motion stays close to the head"), Offset.Y < 0 && Offset.Y > -WarFloatingCombatText::RegionHeight + 32);
            TestTrue(TEXT("Burst speed is bounded"), N.Speed >= 1 && N.Speed <= 5);
            if (N.RecipientId == 2) TestEqual(TEXT("Other targets retain isolated timing"), N.Speed, 1.f);
        }
    }
    TestTrue(TEXT("Sustained rapid procs scroll substantially faster"), Numbers.Last().Speed >= 4);
    TestEqual(TEXT("Critical styling preserves the effective damage amount"), Numbers.Last().Amount, 17.f);
    WarFloatingCombatText::Advance(Numbers, 4.3);
    TestTrue(TEXT("Burst leaves no lingering backlog"), Numbers.IsEmpty());
    Add(1, TEXT("Heal"), 12, 5);
    TestEqual(TEXT("Quiet-period timing returns to one second"), Numbers.Last().Speed, 1.f);
    for (int32 I = 0; I < 50; ++I) Add(1, TEXT("Hit"), 10, 5);
    TestEqual(TEXT("Simultaneous procs respect the per-head cap"), Numbers.Num(), WarFloatingCombatText::MaxPerRecipient);
    for (uint32 I = 2; I < 100; ++I) Add(I, TEXT("Hit"), 10, 5);
    TestEqual(TEXT("Area effects respect the total cap"), Numbers.Num(), WarFloatingCombatText::MaxNumbers);
    WarFloatingCombatText::Advance(Numbers, 0);
    TestTrue(TEXT("Travel clock reset clears old numbers"), Numbers.IsEmpty());

    auto* Instance = NewObject<UGameInstance>(GEngine); Instance->AddToRoot(); Instance->InitializeStandalone();
    auto* World = Instance->GetWorld();
    // ProcessEvent (including native RPC dispatch) requires initialized actors.
    World->InitializeActorsForPlay(FURL());
    auto* Source = World->SpawnActor<AWarCharacter>();
    auto* Target = World->SpawnActor<AWarEnemy>();
    auto* Controller = World->SpawnActor<AWarPlayerController>();
    Controller->SetPlayer(NewObject<ULocalPlayer>(GEngine));
    Controller->Possess(Source); Controller->SetCombatShakeIntensity(0);
    Controller->PlayerState=World->SpawnActor<AWarPlayerState>(); Source->SetPlayerState(Controller->PlayerState);
    WarCombatFeedback::Emit(Source, Target, TEXT("Heal"), 25);
    TestEqual(TEXT("Authoritative outgoing NPC effect reaches floating UI"), Controller->GetFloatingCombatNumbers().Num(), 1);
    if (!Controller->GetFloatingCombatNumbers().IsEmpty())
    {
        TestTrue(TEXT("Recipient is the NPC, independent of selection"), Controller->GetFloatingCombatNumbers()[0].Recipient.Get() == Target);
        TestEqual(TEXT("Effective healing reaches the UI unchanged"), Controller->GetFloatingCombatNumbers()[0].Amount, 25.f);
    }
    auto* Ally = World->SpawnActor<AWarCharacter>();
    auto* OtherController = World->SpawnActor<AWarPlayerController>();
    OtherController->SetPlayer(NewObject<ULocalPlayer>(GEngine)); OtherController->Possess(Ally);
    OtherController->PlayerState=World->SpawnActor<AWarPlayerState>(); Ally->SetPlayerState(OtherController->PlayerState);
    Controller->GetPlayerState<AWarPlayerState>()->SetDevelopmentRealm(EWarRealm::Aegis);
    OtherController->GetPlayerState<AWarPlayerState>()->SetDevelopmentRealm(EWarRealm::Aegis);
    WarCombatFeedback::Emit(Source, Ally, TEXT("Heal"), 30);
    TestEqual(TEXT("Healing a player also floats over the recipient"), Controller->GetFloatingCombatNumbers().Num(), 2);
    TestFalse(TEXT("Authority carries friendly recipient relationship"),Controller->GetFloatingCombatNumbers().Last().bEnemy);
    TestTrue(TEXT("Recipient sees no outgoing number for another player's healing"), OtherController->GetFloatingCombatNumbers().IsEmpty());
    WarCombatFeedback::Emit(Source, Source, TEXT("Heal"), 15);
    TestEqual(TEXT("Self-healing emits exactly one number"), Controller->GetFloatingCombatNumbers().Num(), 3);
    TestFalse(TEXT("Self healing uses friendly settings"),Controller->GetFloatingCombatNumbers().Last().bEnemy);
    Controller->ClientCombatNotice(3, TEXT("Heal"), TEXT("duplicate"), 999, Target->GetUniqueID(), Target, Anchor);
    TestEqual(TEXT("Duplicate RPC cannot create another floating number"), Controller->GetFloatingCombatNumbers().Num(), 3);
    for (int32 I = 1; I <= 160; ++I) WarCombatFeedback::Emit(Source, Target, TEXT("Heal"), I);
    if (TestFalse(TEXT("Owner receives confirmed feedback"), Controller->GetCombatNotices().IsEmpty()))
        TestEqual(TEXT("Owner budget admits bursts but remains capped at 128 notices"), Controller->GetCombatNotices().Last().Amount, 125.f);
    Numbers.Reset();
    WarFloatingCombatText::Add(Numbers, 1, Target, WarFloatingCombatText::HeadAnchor(Target), TEXT("Hit"), 5, 0);
    const FVector Before = Numbers[0].Anchor;
    Target->SetActorLocation(Target->GetActorLocation() + FVector(100, 0, 0));
    WarFloatingCombatText::Advance(Numbers, .1);
    TestTrue(TEXT("Numbers follow moving recipients"), Numbers[0].Anchor.X > Before.X + 90);
    const FVector LastAnchor = Numbers[0].Anchor;
    Target->Destroy();
    WarFloatingCombatText::Advance(Numbers, .2);
    TestEqual(TEXT("Lethal despawns preserve a short-lived last position"), Numbers[0].Anchor, LastAnchor);
    Instance->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); Instance->RemoveFromRoot();
    GConfig->UnloadFile(TestIni);
    return true;
}
#endif
