#include "WarPlayerController.h"
#include "WarInterfaceWidget.h"
#include "WarInventoryWidget.h"
#include "WarQuestLogWidget.h"
#include "WarWorldEditWidget.h"
#include "WarCityServiceWidget.h"
#include "Misc/ConfigCacheIni.h"
#include "AudioDevice.h"
#include "Engine/World.h"

void AWarPlayerController::BeginPlay()
{
    Super::BeginPlay();
    if (!IsLocalController()) return;
    float Look = 1, Zoom = 1;
    bool InvertX = false, InvertY = false;
    GConfig->GetFloat(TEXT("AegisWar.Interface"), TEXT("LookSensitivity"), Look, GGameUserSettingsIni);
    GConfig->GetFloat(TEXT("AegisWar.Interface"), TEXT("ZoomSensitivity"), Zoom, GGameUserSettingsIni);
    GConfig->GetBool(TEXT("AegisWar.Interface"), TEXT("InvertX"), InvertX, GGameUserSettingsIni);
    GConfig->GetBool(TEXT("AegisWar.Interface"), TEXT("InvertY"), InvertY, GGameUserSettingsIni);
    GConfig->GetFloat(TEXT("AegisWar.Interface"), TEXT("MasterVolume"), InterfaceVolume, GGameUserSettingsIni);
    SetInterfaceVolume(InterfaceVolume);
    LocalCameraState.SetPreferences(Look, Zoom, InvertX, InvertY);
}

void AWarPlayerController::SaveInterfacePreferences()
{
    GConfig->SetFloat(TEXT("AegisWar.Interface"), TEXT("LookSensitivity"), LocalCameraState.LookSensitivity, GGameUserSettingsIni);
    GConfig->SetFloat(TEXT("AegisWar.Interface"), TEXT("ZoomSensitivity"), LocalCameraState.ZoomSensitivity, GGameUserSettingsIni);
    GConfig->SetBool(TEXT("AegisWar.Interface"), TEXT("InvertX"), LocalCameraState.bInvertX, GGameUserSettingsIni);
    GConfig->SetBool(TEXT("AegisWar.Interface"), TEXT("InvertY"), LocalCameraState.bInvertY, GGameUserSettingsIni);
    GConfig->SetFloat(TEXT("AegisWar.Interface"), TEXT("MasterVolume"), InterfaceVolume, GGameUserSettingsIni);
    GConfig->Flush(false, GGameUserSettingsIni);
}

bool AWarPlayerController::IsInterfaceOpen() const
{
    return InterfaceWidget && InterfaceWidget->IsInViewport();
}

void AWarPlayerController::CloseInterface()
{
    if (!IsInterfaceOpen()) return;
    InterfaceWidget->RemoveFromParent();
    SetInputMode(FInputModeGameOnly());
    SetIgnoreMoveInput(false);
    SetIgnoreLookInput(false);
    bShowMouseCursor = false;
}

bool AWarPlayerController::CloseAllPanels()
{
    bool Closed = false;
    // Each panel owns one paired input lock. Close directly even during an entry failure.
    for (UUserWidget* Panel : {static_cast<UUserWidget*>(InterfaceWidget.Get()), static_cast<UUserWidget*>(InventoryWidget.Get()),
        static_cast<UUserWidget*>(QuestLogWidget.Get()), static_cast<UUserWidget*>(WorldEditWidget.Get()), static_cast<UUserWidget*>(CityServiceWidget.Get())})
    {
        if (!Panel || !Panel->IsInViewport()) continue;
        Panel->RemoveFromParent();
        SetIgnoreMoveInput(false);
        SetIgnoreLookInput(false);
        Closed = true;
    }
    if (Closed) { SetInputMode(FInputModeGameOnly()); bShowMouseCursor = false; }
    return Closed;
}

void AWarPlayerController::ShowInterface(FName Page)
{
    if (!IsLocalController() || !GetLocalPlayer() || !GetPawn() || !LastEntryFailure.IsEmpty()) return;
    if (IsInterfaceOpen()) { InterfaceWidget->ShowPage(Page); return; }
    CloseAllPanels();
    if (!InterfaceWidget) InterfaceWidget = CreateWidget<UWarInterfaceWidget>(this);
    if (!InterfaceWidget) return;
    InterfaceWidget->ShowPage(Page);
    InterfaceWidget->AddToViewport(20);
    FInputModeGameAndUI Mode;
    Mode.SetWidgetToFocus(InterfaceWidget->TakeWidget());
    Mode.SetHideCursorDuringCapture(false);
    SetInputMode(Mode);
    SetIgnoreMoveInput(true);
    SetIgnoreLookInput(true);
    bShowMouseCursor = true;
}

void AWarPlayerController::ToggleMenu()
{
    if (!LastEntryFailure.IsEmpty()) return;
    if (IsEditingUi()) { SetEditingUi(false); return; }
    if (!CloseAllPanels()) ShowInterface(TEXT("Menu"));
}
void AWarPlayerController::ToggleMap()
{
    if (IsInterfaceOpen() && InterfaceWidget->GetPage() == TEXT("Map")) CloseInterface();
    else ShowInterface(TEXT("Map"));
}
void AWarPlayerController::ToggleCharacter()
{
    if (IsInterfaceOpen() && InterfaceWidget->GetPage() == TEXT("Character")) CloseInterface();
    else ShowInterface(TEXT("Character"));
}
void AWarPlayerController::ToggleGuide() { ShowInterface(TEXT("Guide")); }

void AWarPlayerController::SetInterfaceVolume(float Volume)
{
    InterfaceVolume = FMath::IsFinite(Volume) ? FMath::Clamp(Volume, 0.f, 1.f) : 1.f;
    if (GetWorld())
        if (auto Device = GetWorld()->GetAudioDevice()) Device->SetTransientPrimaryVolume(InterfaceVolume);
}
