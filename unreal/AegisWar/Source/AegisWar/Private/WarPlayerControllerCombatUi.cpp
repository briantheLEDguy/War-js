#include "WarPlayerController.h"
#include "Misc/ConfigCacheIni.h"

const FWarCombatUiSettings& AWarPlayerController::GetCombatUiSettings()
{
    if (!bCombatUiLoaded) { bCombatUiLoaded=true; CombatUiSettings.Load(GGameUserSettingsIni); }
    return CombatUiSettings;
}
void AWarPlayerController::SaveCombatUiSettings() { GetCombatUiSettings(); CombatUiSettings.Save(GGameUserSettingsIni); }
void AWarPlayerController::SetCombatUiStyle(int32 I,const FWarCombatUiStyle& Style,bool bSave)
{
    GetCombatUiSettings(); CombatUiSettings.Set(I,Style);
    // Hiding a category immediately releases its slots; it cannot crowd visible effects.
    FloatingCombatNumbers.RemoveAll([this](const auto& N) {
        const auto P=N.Kind==TEXT("Heal")?EWarCombatUiPart::Healing:N.Kind==TEXT("CriticalHit")?EWarCombatUiPart::Critical:EWarCombatUiPart::Damage;
        return !CombatUiSettings.Styles[WarCombatUi::Id(P,N.bEnemy)].Visible;
    });
    if (bSave) SaveCombatUiSettings();
}
void AWarPlayerController::MoveCombatUi(int32 I,FVector2D Delta,FVector2D View,float Scale,bool bSave)
{ GetCombatUiSettings(); WarCombatUi::Move(CombatUiSettings,I,Delta,View,Scale); if (bSave) SaveCombatUiSettings(); }
void AWarPlayerController::ResetCombatUi(int32 I)
{ GetCombatUiSettings(); if (I==INDEX_NONE) CombatUiSettings=FWarCombatUiSettings(); else CombatUiSettings.Reset(I); SaveCombatUiSettings(); }
void AWarPlayerController::CopyCombatUiSide(int32 I)
{ GetCombatUiSettings(); CombatUiSettings.CopySide(I); if (I>=0 && I<20) SetCombatUiStyle((I+10)%20,CombatUiSettings.Styles[(I+10)%20]); }
