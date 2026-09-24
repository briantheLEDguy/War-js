#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarFrontendWidget.h"
#include "WarGameMode.h"
#include "WarPlayerController.h"
#include "WarCharacterVisualDefinition.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerStart.h"
#include "TimerManager.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
    void EntryButtons(const TSharedRef<SWidget>& Widget, TArray<TSharedRef<SButton>>& Buttons)
    {
        if (Widget->GetTypeAsString() == TEXT("SButton"))
        {
            const auto Button = StaticCastSharedRef<SButton>(Widget);
            if (Button->GetContent()->GetTypeAsString() == TEXT("STextBlock")) Buttons.Add(Button);
        }
        auto* Children = Widget->GetChildren();
        for (int32 Index = 0; Children && Index < Children->Num(); ++Index)
            EntryButtons(Children->GetChildAt(Index), Buttons);
    }
    FString ButtonLabel(const TSharedRef<SButton>& Button)
    { return StaticCastSharedRef<STextBlock>(Button->GetContent())->GetText().ToString(); }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarFrontendTest, "AegisWar.Foundation.CharacterFrontend",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FWarFrontendTest::RunTest(const FString& Parameters)
{
    FString Error;
    auto* Visual = NewObject<UWarCharacterVisualDefinition>();
    Visual->ProfileKey = TEXT("civic_battle_prelate_m");
    TestTrue(TEXT("Own model with implicit source identity is allowed"), Visual->HasPlayableSourceIdentity());
    Visual->SourceProfileKey = Visual->ProfileKey;
    TestTrue(TEXT("Own imported Prelate model is allowed"), Visual->HasPlayableSourceIdentity());
    Visual->SourceProfileKey = TEXT("npc_frontier_sunmeadow_empire_herbalist");
    TestFalse(TEXT("An herbalist cannot stand in for a playable Prelate"), Visual->HasPlayableSourceIdentity());
    Visual->SourceProfileKey = TEXT("civic_ember_arcanist_m");
    TestFalse(TEXT("A different class cannot stand in for a playable Prelate"), Visual->HasPlayableSourceIdentity());
    for (const FString& Name : {TEXT("Mara Vell"), TEXT("Aegis-Recruit"), TEXT("O'Rellan")})
        TestTrue(TEXT("Valid original character name"), UWarFrontendWidget::ValidateCharacterName(Name, Error));
    for (const FString& Name : {TEXT(""), TEXT("ab"), TEXT("---"), TEXT(" abc"), TEXT("abc "), TEXT("Recruit123"), TEXT("abc\nxyz"), TEXT("abcdefghijklmnopqrstuvwxyz")})
    {
        TestFalse(TEXT("Invalid name rejected"), UWarFrontendWidget::ValidateCharacterName(Name, Error));
        TestFalse(TEXT("Invalid name gives actionable feedback"), Error.IsEmpty());
    }
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Test world"), World)) return false;
    auto& Context = GEngine->CreateNewWorldContext(EWorldType::Game); Context.SetCurrentWorld(World);
    auto* Mode = World->SpawnActor<AWarGameMode>();
    auto* Player = World->SpawnActor<AWarPlayerController>();
    Mode->HandleStartingNewPlayer_Implementation(Player);
    TestNull(TEXT("Ordinary entry waits for character selection without spawning"), Player->GetPawn());
    TestTrue(TEXT("Login does not produce a missing-visual error"), Player->GetEntryFailure().IsEmpty());
    TestNull(TEXT("No character visual is assigned before creation"), Player->GetCreatedCharacterVisual());

    Player->BeginCharacterEntry(Visual);
    Player->CompleteCharacterEntry();
    TestTrue(TEXT("Entry stays pending while there is no pawn"), Player->IsCharacterEntryPending());
    TestTrue(TEXT("Loading is not a clearance failure"), Player->GetEntryFailure().IsEmpty());
    TestTrue(TEXT("The selected visual survives deferred spawn"), Player->GetCreatedCharacterVisual() == Visual);
    Player->ServerCreateDevelopmentCharacter_Implementation(TEXT("Ignored duplicate"), NAME_None, NAME_None, NAME_None);
    TestTrue(TEXT("Duplicate submissions cannot replace the loading character"), Player->GetCreatedCharacterVisual() == Visual);

    const FText Failure = FText::FromString(TEXT("Arrival content did not load. Please retry character entry."));
    Player->RecordEntryFailure(Failure);
    TestFalse(TEXT("A real streaming failure releases the entry controls"), Player->IsCharacterEntryPending());
    TestEqual(TEXT("The real failure is preserved"), Player->GetEntryFailure().ToString(), Failure.ToString());
    TestNull(TEXT("Failed entry releases its draft visual"), Player->GetCreatedCharacterVisual());
    Player->BeginCharacterEntry(Visual);
    TestTrue(TEXT("Retry clears the previous failure"), Player->GetEntryFailure().IsEmpty());

    auto* Pawn = World->SpawnActor<APawn>();
    auto* Start = World->SpawnActor<APlayerStart>();
    Player->SetPawn(Pawn);
    Player->CompleteCharacterEntry();
    TestTrue(TEXT("An assigned but unpossessed pawn does not finish entry"), Player->IsCharacterEntryPending());
    // Exercise the actual restart/possession callback on a later tick, as city streaming does.
    World->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateLambda([Mode, Player, Start]() {
        Mode->RestartPlayerAtPlayerStart(Player, Start);
    }));
    World->Tick(LEVELTICK_All, 0.1f);
    TestTrue(TEXT("Deferred restart possesses the pawn"), Pawn->GetController() == Player);
    TestFalse(TEXT("Deferred possession completes entry"), Player->IsCharacterEntryPending());
    TestTrue(TEXT("Successful entry retains its visual for respawn"), Player->GetCreatedCharacterVisual() == Visual);
    TestTrue(TEXT("Successful entry has no error"), Player->GetEntryFailure().IsEmpty());
    Player->ServerCreateDevelopmentCharacter_Implementation(TEXT("Ignored duplicate"), NAME_None, NAME_None, NAME_None);
    TestTrue(TEXT("Retry after success keeps the same pawn"), Player->GetPawn() == Pawn);
    TestTrue(TEXT("Retry after success does not report a login failure"), Player->GetEntryFailure().IsEmpty());

    Player->UnPossess();
    Player->BeginCharacterEntry(Visual);
    AddExpectedError(TEXT("Player entry refused: This map has no valid PlayerStart"), EAutomationExpectedErrorFlags::Contains, 1);
    Mode->RestartPlayerAtPlayerStart(Player, nullptr);
    TestFalse(TEXT("A missing arrival start ends pending entry"), Player->IsCharacterEntryPending());
    TestTrue(TEXT("Missing start retains its actionable error"), Player->GetEntryFailure().ToString().Contains(TEXT("no valid PlayerStart")));
    auto* Frontend = NewObject<UWarFrontendWidget>(World);
    Frontend->Initialize();
    const auto Entry = Frontend->TakeWidget();
    TArray<TSharedRef<SButton>> Buttons;
    EntryButtons(Entry, Buttons);
    TestTrue(TEXT("Login exposes a primary local entry action"), !Buttons.IsEmpty()
        && ButtonLabel(Buttons[0]) == TEXT("Local development login"));
    const auto Click = [this, &Entry](const FString& Label) {
        TArray<TSharedRef<SButton>> Current;
        EntryButtons(Entry, Current);
        for (const auto& Button : Current)
            if (ButtonLabel(Button) == Label) { Button->SimulateClick(); return true; }
        AddError(TEXT("Missing entry button: ") + Label); return false;
    };
    if (Click(TEXT("Local development login")))
    {
        Buttons.Reset(); EntryButtons(Entry, Buttons);
        TestTrue(TEXT("Local entry opens character creation without an account companion"),
            Buttons.ContainsByPredicate([](const auto& Button) { return ButtonLabel(Button) == TEXT("Review character"); }));
        Click(TEXT("Back to login"));
    }
    if (Click(TEXT("Developer account")))
    {
        Buttons.Reset(); EntryButtons(Entry, Buttons);
        TestTrue(TEXT("Optional account page retains GitHub sign-in"),
            Buttons.ContainsByPredicate([](const auto& Button) { return ButtonLabel(Button) == TEXT("Sign in with GitHub"); }));
        Click(TEXT("Back to login"));
        Buttons.Reset(); EntryButtons(Entry, Buttons);
        TestTrue(TEXT("Leaving account tools returns to usable local login"), !Buttons.IsEmpty()
            && ButtonLabel(Buttons[0]) == TEXT("Local development login"));
    }
    World->DestroyWorld(false); GEngine->DestroyWorldContext(World);
    return true;
}
#endif
