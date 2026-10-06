#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "EnhancedPlayerInput.h"
#include "GameFramework/InputSettings.h"
#include "WarControlSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarInputRenderingTest, "AegisWar.Foundation.InputRenderingIsolation",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarInputRenderingTest::RunTest(const FString&)
{
    // Read the actual merged Engine/project configuration, not a copied list of
    // game bindings. Engine debug exec runs before normal gameplay consumption.
    auto* Input = NewObject<UPlayerInput>(GetTransientPackage(), UInputSettings::GetDefaultPlayerInputClass());
    for (const FKey Key : {EKeys::F1, EKeys::F2, EKeys::F3, EKeys::F4, EKeys::F5})
    {
        TestFalse(*FString::Printf(TEXT("%s cannot execute an inherited view-mode command"), *Key.ToString()),
            Input->DebugExecBindings.ContainsByPredicate([Key](const FKeyBind& Bind) {
                return Bind.Key == Key && Bind.Command.StartsWith(TEXT("viewmode "), ESearchCase::IgnoreCase);
            }));
        TestTrue(*FString::Printf(TEXT("%s has no debug command before gameplay dispatch"), *Key.ToString()),
            Input->GetBind(Key).IsEmpty());
    }
    TestTrue(TEXT("GM retains its F2 gameplay shortcut"), WarControls::Defaults().ContainsByPredicate([](const auto& Bind) {
        return Bind.Action == TEXT("GM") && Bind.Key == EKeys::F2;
    }));
    FString Error;
    for (const FKey Key : {EKeys::F2, EKeys::F3, EKeys::F4, EKeys::F5})
        TestTrue(TEXT("Former view-mode keys remain valid remapped controls"), WarControls::Validate(TEXT("GM"), Key, {}, Error));
    TestTrue(TEXT("Unrelated screenshot shortcut is retained"), Input->DebugExecBindings.ContainsByPredicate([](const FKeyBind& Bind) {
        return Bind.Key == EKeys::F9 && Bind.Command == TEXT("shot showui");
    }));
    TestTrue(TEXT("Unrelated fullscreen shortcut is retained"), Input->DebugExecBindings.ContainsByPredicate([](const FKeyBind& Bind) {
        return Bind.Key == EKeys::F11 && Bind.Command == TEXT("MainFrame.ToggleFullscreen");
    }));
    return true;
}
#endif
