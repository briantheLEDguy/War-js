#include "WarPlayerController.h"
#include "WarActionBarWidget.h"
#include "Misc/ConfigCacheIni.h"

const TArray<FWarActionBarLayout>& AWarPlayerController::GetActionBars()
{
    if (bActionBarsLoaded) return ActionBars;
    bActionBarsLoaded = true;
    FString Ids;
    if (!GConfig->GetString(TEXT("AegisWar.ActionBar"), TEXT("Bars"), Ids, GGameUserSettingsIni))
        ActionBars.Add(FWarActionBarLayout());
    else
    {
        TArray<FString> Entries; Ids.ParseIntoArray(Entries, TEXT(","), true);
        for (const FString& Entry : Entries)
        {
            int32 Id = INDEX_NONE;
            if (!LexTryParseString(Id, *Entry) || Id < 0 || Id > (MAX_int32 / 10 - 1)
                || ActionBars.ContainsByPredicate([Id](const auto& Bar) { return Bar.Id == Id; })) continue;
            FWarActionBarLayout Bar; Bar.Id = Id;
            const FString Prefix = FString::Printf(TEXT("Bar%d"), Id);
            GConfig->GetInt(TEXT("AegisWar.ActionBar"), *(Prefix + TEXT("Buttons")), Bar.Buttons, GGameUserSettingsIni);
            Bar.Buttons = FMath::Clamp(Bar.Buttons, 1, 10);
            double X = Bar.Position.X, Y = Bar.Position.Y;
            GConfig->GetDouble(TEXT("AegisWar.ActionBar"), *(Prefix + TEXT("X")), X, GGameUserSettingsIni);
            GConfig->GetDouble(TEXT("AegisWar.ActionBar"), *(Prefix + TEXT("Y")), Y, GGameUserSettingsIni);
            Bar.Position = FVector2D(FMath::IsFinite(X) ? FMath::Clamp(X, 0., 1.) : 0.5,
                FMath::IsFinite(Y) ? FMath::Clamp(Y, 0., 1.) : 0.86);
            ActionBars.Add(Bar);
            NextActionBarId = FMath::Max(NextActionBarId, Id + 1);
        }
    }
    int32 SavedNext = 1;
    GConfig->GetInt(TEXT("AegisWar.ActionBar"), TEXT("NextId"), SavedNext, GGameUserSettingsIni);
    if (SavedNext > 0 && SavedNext < MAX_int32 / 10) NextActionBarId = FMath::Max(NextActionBarId, SavedNext);
    return ActionBars;
}

bool AWarPlayerController::HasActionSlot(int32 Slot)
{
    if (Slot < 0) return false;
    return GetActionBars().ContainsByPredicate([Slot](const auto& Bar) { return Slot / 10 == Bar.Id && Slot % 10 < Bar.Buttons; });
}

void AWarPlayerController::SaveActionBars()
{
    TArray<FString> Ids;
    for (const auto& Bar : GetActionBars())
    {
        Ids.Add(FString::FromInt(Bar.Id));
        const FString Prefix = FString::Printf(TEXT("Bar%d"), Bar.Id);
        GConfig->SetInt(TEXT("AegisWar.ActionBar"), *(Prefix + TEXT("Buttons")), Bar.Buttons, GGameUserSettingsIni);
        GConfig->SetDouble(TEXT("AegisWar.ActionBar"), *(Prefix + TEXT("X")), Bar.Position.X, GGameUserSettingsIni);
        GConfig->SetDouble(TEXT("AegisWar.ActionBar"), *(Prefix + TEXT("Y")), Bar.Position.Y, GGameUserSettingsIni);
    }
    GConfig->SetString(TEXT("AegisWar.ActionBar"), TEXT("Bars"), *FString::Join(Ids, TEXT(",")), GGameUserSettingsIni);
    GConfig->SetInt(TEXT("AegisWar.ActionBar"), TEXT("NextId"), NextActionBarId, GGameUserSettingsIni);
    GConfig->Flush(false, GGameUserSettingsIni);
}

void AWarPlayerController::RebuildActionBars()
{
    if (ActionBarWidget) ActionBarWidget->RemoveFromParent();
    ActionBarWidget = nullptr;
    BindControlKeys();
}

int32 AWarPlayerController::AddActionBar(int32 Buttons)
{
    GetActionBars();
    if (Buttons < 1 || Buttons > 10 || NextActionBarId >= MAX_int32 / 10) return INDEX_NONE;
    FWarActionBarLayout Bar; Bar.Id = NextActionBarId++; Bar.Buttons = Buttons;
    Bar.Position = FVector2D(0.5, 0.5 + (ActionBars.Num() % 4) * 0.09);
    ActionBars.Add(Bar);
    SaveActionBars(); RebuildActionBars();
    return Bar.Id;
}

void AWarPlayerController::RemoveActionBar(int32 Id)
{
    GetActionBars();
    if (!ActionBars.RemoveAll([Id](const auto& Bar) { return Bar.Id == Id; })) return;
    for (int32 Button = 0; Button < 10; ++Button)
    {
        const FName Key = WarActionBar::Binding(Id * 10 + Button);
        ControlKeys.Remove(Key);
        GConfig->RemoveKey(TEXT("AegisWar.Controls"), *Key.ToString(), GGameUserSettingsIni);
    }
    SaveActionBars(); RebuildActionBars();
}

void AWarPlayerController::ResizeActionBar(int32 Id, int32 Buttons)
{
    GetActionBars();
    if (Buttons < 1 || Buttons > 10) return;
    for (auto& Bar : ActionBars) if (Bar.Id == Id) Bar.Buttons = Buttons;
    SaveActionBars(); RebuildActionBars();
}

void AWarPlayerController::MoveActionBar(int32 Id, FVector2D Position, bool bSave)
{
    if (!FMath::IsFinite(Position.X) || !FMath::IsFinite(Position.Y)) return;
    for (auto& Bar : ActionBars) if (Bar.Id == Id)
        Bar.Position = FVector2D(FMath::Clamp(Position.X, 0., 1.), FMath::Clamp(Position.Y, 0., 1.));
    if (bSave) SaveActionBars();
}

void AWarPlayerController::SetEditingUi(bool bEditing)
{
    if (bEditing) CloseAllPanels();
    bEditingUi = bEditing;
    bShowMouseCursor = bEditing;
    if (bEditing) { FInputModeGameAndUI Mode; Mode.SetHideCursorDuringCapture(false); SetInputMode(Mode); }
    else { SaveActionBars(); SetInputMode(FInputModeGameOnly()); ShowInterface(TEXT("UI Settings")); }
}
