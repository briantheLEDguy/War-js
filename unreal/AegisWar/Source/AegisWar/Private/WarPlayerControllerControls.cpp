#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarControlSettings.h"
#include "Misc/ConfigCacheIni.h"

FKey AWarPlayerController::GetControlKey(FName Action) const
{
    if (const auto* Key = ControlKeys.Find(Action)) return *Key;
    if (WarActionBar::IsSlotBinding(Action)) return EKeys::Invalid;
    for (const auto& Entry : WarControls::Defaults()) if (Entry.Action == Action) return Entry.Key;
    return EKeys::Invalid;
}
void AWarPlayerController::LoadControlKeys()
{
    if (!ControlKeys.IsEmpty()) return;
    auto Entries = WarControls::Defaults();
    const bool bHasFirstBar = GetActionBars().ContainsByPredicate([](const auto& Bar) { return Bar.Id == 0; });
    Entries.RemoveAll([bHasFirstBar](const auto& Entry) { return WarActionBar::IsSlotBinding(Entry.Action) && !bHasFirstBar; });
    for (const auto& Bar : GetActionBars()) if (Bar.Id != 0) for (int32 Button = 0; Button < 10; ++Button)
        Entries.Add({WarActionBar::Binding(Bar.Slot(Button)), TEXT("Action button"), EKeys::Invalid});
    // Existing explicit choices take priority over defaults introduced by a new UI version.
    TSet<FName> Explicit;
    for (const auto& Entry : Entries)
    {
        FString Stored, Error;
        if (GConfig->GetString(TEXT("AegisWar.Controls"), *Entry.Action.ToString(), Stored, GGameUserSettingsIni)
            && WarControls::Validate(Entry.Action, FKey(FName(*Stored)), ControlKeys, Error))
        { ControlKeys.Add(Entry.Action, FKey(FName(*Stored))); Explicit.Add(Entry.Action); }
    }
    for (const auto& Entry : Entries) if (!Explicit.Contains(Entry.Action))
    {
        FString Error;
        ControlKeys.Add(Entry.Action, WarControls::Validate(Entry.Action, Entry.Key, ControlKeys, Error) ? Entry.Key : EKeys::Invalid);
    }
}
bool AWarPlayerController::SetControlKey(FName Action,FKey Key,FString& Error)
{
    LoadControlKeys();
    if (WarActionBar::IsSlotBinding(Action) && !HasActionSlot(FCString::Atoi(*Action.ToString().Mid(10)) - 1))
    { Error = TEXT("That button is not on an active bar."); return false; }
    if (!WarControls::Validate(Action,Key,ControlKeys,Error)) return false;
    ControlKeys.Add(Action,Key);
    GConfig->SetString(TEXT("AegisWar.Controls"),*Action.ToString(),*Key.GetFName().ToString(),GGameUserSettingsIni);
    GConfig->Flush(false,GGameUserSettingsIni);
    BindControlKeys();
    if (auto* Controlled = Cast<AWarCharacter>(GetPawn())) Controlled->RefreshControlMappings();
    return true;
}
void AWarPlayerController::ResetControlKeys()
{
    ControlKeys.Empty();
    for (const auto& Bar : GetActionBars()) for (int32 Button = 0; Button < 10; ++Button)
    {
        const FName Action = WarActionBar::Binding(Bar.Slot(Button));
        ControlKeys.Add(Action, EKeys::Invalid);
        GConfig->SetString(TEXT("AegisWar.Controls"), *Action.ToString(), TEXT("None"), GGameUserSettingsIni);
    }
    for (const auto& Entry : WarControls::Defaults())
    {
        if (WarActionBar::IsSlotBinding(Entry.Action) && !HasActionSlot(FCString::Atoi(*Entry.Action.ToString().Mid(10)) - 1)) continue;
        ControlKeys.Add(Entry.Action,Entry.Key);
        GConfig->SetString(TEXT("AegisWar.Controls"),*Entry.Action.ToString(),*Entry.Key.GetFName().ToString(),GGameUserSettingsIni);
    }
    GConfig->Flush(false,GGameUserSettingsIni);
    BindControlKeys();
    if (auto* Controlled = Cast<AWarCharacter>(GetPawn())) Controlled->RefreshControlMappings();
}
