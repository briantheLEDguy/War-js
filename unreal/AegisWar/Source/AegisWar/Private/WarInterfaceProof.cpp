#include "WarInterfaceProof.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarGameplayEffects.h"
#include "WarContentSubsystem.h"
#include "WarInterfaceCatalog.h"
#include "WarWorldEditSubsystem.h"
#include "AbilitySystemComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "UnrealClient.h"
#include "Misc/ConfigCacheIni.h"
#include "Framework/Application/SlateApplication.h"
#include "Layout/WidgetPath.h"
#include "Widgets/SWindow.h"
#include "TimerManager.h"

namespace
{
    TSharedPtr<SWidget> FindBarHandle(const TSharedRef<SWidget>& Widget)
    {
        if (Widget->GetTypeAsString() == TEXT("SWarBarHandle") && Widget->GetVisibility().IsVisible()) return Widget;
        FChildren* Children = Widget->GetChildren();
        for (int32 Index = 0; Children && Index < Children->Num(); ++Index)
            if (auto Found = FindBarHandle(Children->GetChildAt(Index))) return Found;
        return nullptr;
    }
    bool VerifyBarDrag(AWarPlayerController* PC)
    {
        if (PC->GetActionBars().IsEmpty()) return true;
        auto& Slate = FSlateApplication::Get();
        TSharedPtr<SWidget> Handle;
        for (const auto& Window : Slate.GetTopLevelWindows())
            if ((Handle = FindBarHandle(Window))) break;
        FWidgetPath Path;
        if (!Handle || !Slate.GeneratePathToWidgetUnchecked(Handle.ToSharedRef(), Path) || !Path.IsValid()) return false;
        // Generated navigation paths omit per-widget pointer entries required by the event router.
        TArray<FWidgetAndPointer> PointerPath;
        for (int32 Index = 0; Index < Path.Widgets.Num(); ++Index) PointerPath.Emplace(Path.Widgets[Index]);
        Path = FWidgetPath(MakeArrayView(PointerPath));
        const auto Before = PC->GetActionBars()[0];
        const FVector2D Start = Handle->GetCachedGeometry().GetAbsolutePosition() + FVector2D(15, 8);
        const FVector2D End = Start + FVector2D(Before.Position.X > 0.5 ? -40 : 40, -25);
        const TSet<FKey> Pressed{EKeys::LeftMouseButton};
        // An offscreen window cannot be OS-hit-tested. Route its verified Slate path using the real cursor index.
        const uint32 Pointer = FSlateApplication::CursorPointerIndex;
        UE_LOG(LogTemp, Display, TEXT("Action bar proof: mouse down"));
        Slate.RoutePointerDownEvent(Path, FPointerEvent(Pointer, Start, Start, Pressed, EKeys::LeftMouseButton, 0, FModifierKeysState()));
        UE_LOG(LogTemp, Display, TEXT("Action bar proof: mouse move, capture=%d"), Handle->HasMouseCapture());
        Slate.RoutePointerMoveEvent(Path, FPointerEvent(Pointer, End, Start, Pressed, EKeys::Invalid, 0, FModifierKeysState()), false);
        UE_LOG(LogTemp, Display, TEXT("Action bar proof: mouse up"));
        Slate.RoutePointerUpEvent(Path, FPointerEvent(Pointer, End, End, {}, EKeys::LeftMouseButton, 0, FModifierKeysState()));
        const bool bMoved = PC->GetActionBars()[0].Position != Before.Position;
        double SavedX = -1;
        GConfig->GetDouble(TEXT("AegisWar.ActionBar"), *FString::Printf(TEXT("Bar%dX"), Before.Id), SavedX, GGameUserSettingsIni);
        const bool bSaved = FMath::IsNearlyEqual(SavedX, PC->GetActionBars()[0].Position.X);
        UE_LOG(LogTemp, Display, TEXT("Action bar proof: moved=%d saved=%d released=%d"), bMoved, bSaved, !Handle->HasMouseCapture());
        PC->MoveActionBar(Before.Id, Before.Position, true);
        return bMoved && bSaved && !Handle->HasMouseCapture();
    }
}

bool UWarInterfaceProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarInterfaceProof"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentGM"));
#endif
}
TStatId UWarInterfaceProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarInterfaceProof, STATGROUP_Tickables); }

void UWarInterfaceProof::Finish(bool Passed, const FString& Detail)
{
    bFinished = true;
    const auto Folder = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("InterfaceProof"));
    IFileManager::Get().MakeDirectory(*Folder, true);
    const FString Report = FString::Printf(TEXT("{\"passed\":%s,\"detail\":\"%s\",\"fullUiParity\":false}"), Passed ? TEXT("true") : TEXT("false"), *Detail);
    FFileHelper::SaveStringToFile(Report, *FPaths::Combine(Folder, TEXT("report.json")));
    FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
}

void UWarInterfaceProof::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < NextStep) return;
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    const auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    if (!Pawn || !Pawn->IsVisualReady())
    {
        if (Now > 90) Finish(false, TEXT("Player did not initialize"));
        return;
    }
    const auto Check = [this](bool Good, const FString& Detail) { if (!Good) Finish(false, Detail); return Good; };
    const TArray<FName> Pages{TEXT("Menu"), TEXT("Map"), TEXT("Clean Map"), TEXT("Campaign"), TEXT("Character"), TEXT("Options"), TEXT("Guide"), TEXT("GM Tools"), TEXT("Key bindings"), TEXT("UI Settings"), TEXT("Edit UI"), TEXT("World builder")};
    if (FParse::Param(FCommandLine::Get(), TEXT("WarActionBarProof")))
    {
        const int32 EditStep = Pages.IndexOfByKey(FName(TEXT("Edit UI"))) * 2;
        if (Step == 0) Step = EditStep;
        if (Step > EditStep + 1) { Finish(true, TEXT("Action bar drag, saved position and mouse release passed")); return; }
    }
    const auto Folder = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("InterfaceProof"));
    IFileManager::Get().MakeDirectory(*Folder, true);
    if (Step < Pages.Num() * 2)
    {
        const FName Page = Pages[Step / 2];
        if (Step % 2 == 0)
        {
            if (Page == TEXT("Edit UI"))
            {
                PC->SetEditingUi(true);
                if (!Check(PC->IsEditingUi() && !PC->IsMoveInputIgnored() && PC->bShowMouseCursor, TEXT("Edit UI did not release gameplay and expose dragging"))) return;
                ++Step; NextStep = Now + 2; return;
            }
            if (PC->IsEditingUi()) PC->SetEditingUi(false);
            if (Page == TEXT("World builder")) PC->ToggleWorldEditor(); else PC->ShowInterface(Page);
            if (!Check((PC->IsInterfaceOpen() || Page==TEXT("World builder")) && PC->IsMoveInputIgnored() && PC->IsLookInputIgnored() && PC->bShowMouseCursor,
                TEXT("Opening a page did not capture input"))) return;
        }
        else
        {
            if (Page == TEXT("Edit UI") && !Check(VerifyBarDrag(PC), TEXT("Slate bar drag, saved position or mouse release failed"))) return;
            if (FParse::Param(FCommandLine::Get(), TEXT("WarProofScreenshot")))
                FScreenshotRequest::RequestScreenshot(FPaths::Combine(Folder, Page.ToString() + TEXT(".png")), true, false);
        }
    }
    else if (Step == Pages.Num()*2)
    {
        PC->ToggleMenu();
        if (!Check(!PC->IsInterfaceOpen() && !PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored() && !PC->bShowMouseCursor,
            TEXT("Repeated page transitions leaked input locks"))) return;
        PC->ToggleMap(); PC->ToggleMap();
        if (!Check(!PC->IsInterfaceOpen() && !PC->IsMoveInputIgnored(), TEXT("Map toggle did not close"))) return;
        PC->ShowInterface(TEXT("Menu")); PC->ToggleInventory();
        if (!Check(!PC->IsInterfaceOpen() && PC->IsMoveInputIgnored(), TEXT("Inventory handoff failed"))) return;
        PC->ToggleMenu();
        if (!Check(!PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored(), TEXT("Inventory close leaked input locks"))) return;
        PC->ShowInterface(TEXT("Menu")); PC->ToggleQuestLog(); PC->ToggleMenu();
        if (!Check(!PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored(), TEXT("Quest close leaked input locks"))) return;
        PC->ShowInterface(TEXT("Menu")); PC->ToggleWorldEditor(); PC->ToggleMenu();
        if (!Check(!PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored(), TEXT("GM close leaked input locks"))) return;
        if (FParse::Param(FCommandLine::Get(), TEXT("WarProofScreenshot")))
        {
            // Let controller/Slate visibility settle after closing the modal before capturing the HUD.
            FTimerHandle Capture;
            GetWorld()->GetTimerManager().SetTimer(Capture, FTimerDelegate::CreateLambda([Folder] {
                FScreenshotRequest::RequestScreenshot(FPaths::Combine(Folder, TEXT("HUD.png")), true, false);
            }), 0.25f, false);
        }
    }
    else if (Step == Pages.Num()*2+1)
    {
        const auto* Content=PC->GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
        const auto Catalog=FWarInterfaceCatalog::Parse(Content->GetInterfaceCatalogSource());
        if (!Check(Catalog.Pages.Num()==305 && Catalog.Zones.Num()==32, TEXT("Original map/guide catalogs incomplete"))) return;
        auto* Editor=GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
        FString EditError; FName Duplicate;
        if (!Check(Editor && Editor->Open(PC,EditError),TEXT("GM builder did not open"))) return;
        const int32 Before=Editor->GetHistory().GetObjects().Num();
        const FName Template=Editor->GetHistory().GetObjects()[0].Id;
        if (!Check(Editor->Duplicate(PC,Template,Editor->GetHistory().GetRevision(),Duplicate,EditError),TEXT("GM duplicate failed"))) return;
        if (!Check(Editor->GetHistory().GetObjects().Num()==Before+1 && Editor->GetObjectActor(Duplicate),TEXT("GM copy did not spawn a native actor"))) return;
        if (!Check(Editor->ResetDraft(PC,Editor->GetHistory().GetRevision(),EditError) && !Editor->GetObjectActor(Duplicate),TEXT("GM reset did not remove copy"))) return;
        if (!Check(Editor->Undo(PC,false,Editor->GetHistory().GetRevision(),EditError) && Editor->GetObjectActor(Duplicate),TEXT("GM reset undo did not restore copy"))) return;
        if (!Check(Editor->Undo(PC,false,Editor->GetHistory().GetRevision(),EditError) && Editor->GetHistory().GetObjects().Num()==Before,TEXT("GM duplicate undo did not restore world"))) return;
        const auto* PlayerState=PC->GetPlayerState<AWarPlayerState>();
        auto* ASC=PlayerState->GetAbilitySystemComponent();
        const auto* Attributes=PlayerState->GetAttributes();
        ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),25.f);
        ASC->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),15.f);
        PC->ServerGmRestore();
        if (!Check(Attributes->GetHealth()==Attributes->GetMaxHealth() && Attributes->GetMana()==Attributes->GetMaxMana(),TEXT("GM restore failed"))) return;
        FGameplayEffectSpec Cooldown(GetDefault<UWarStrikeCooldownEffect>(),ASC->MakeEffectContext(),1);
        Cooldown.DynamicGrantedTags.AddTag(FGameplayTag::RequestGameplayTag(TEXT("War.Cooldown.DevelopmentStrike")));
        const auto CooldownHandle=ASC->ApplyGameplayEffectSpecToSelf(Cooldown);
        FGameplayEffectSpec OtherEffect(GetDefault<UWarStrikeCooldownEffect>(),ASC->MakeEffectContext(),1);
        const auto OtherHandle=ASC->ApplyGameplayEffectSpecToSelf(OtherEffect);
        PC->ServerGmResetCooldowns();
        if (!Check(!ASC->GetActiveGameplayEffect(CooldownHandle) && ASC->GetActiveGameplayEffect(OtherHandle),TEXT("GM cooldown reset removed unrelated effects"))) return;
        ASC->RemoveActiveGameplayEffect(OtherHandle);
        const auto Location=Pawn->GetActorLocation();
        PC->ServerGmTeleportZone(TEXT("invalid_zone"));
        PC->ServerGmGoToCharacter(TEXT(""));
        if (!Check(Pawn->GetActorLocation().Equals(Location),TEXT("Invalid GM teleport changed position"))) return;
        FString BindingError;
        const auto OriginalKey=PC->GetControlKey(TEXT("Forward"));
        if (!Check(PC->SetControlKey(TEXT("Forward"),EKeys::P,BindingError),TEXT("Control remap rejected valid key"))) return;
        FString StoredKey;
        GConfig->GetString(TEXT("AegisWar.Controls"),TEXT("Forward"),StoredKey,GGameUserSettingsIni);
        const bool SavedKey=StoredKey==TEXT("P") && PC->GetControlKey(TEXT("Forward"))==EKeys::P;
        PC->SetControlKey(TEXT("Forward"),OriginalKey,BindingError);
        if (!Check(SavedKey,TEXT("Control binding storage failed"))) return;
        const auto Camera = PC->GetLocalCameraState();
        PC->GetLocalCameraState().SetPreferences(1.75, 0.5, true, true);
        PC->SaveInterfacePreferences();
        float SavedLook = 0, SavedZoom = 0;
        bool SavedX = false, SavedY = false;
        GConfig->GetFloat(TEXT("AegisWar.Interface"), TEXT("LookSensitivity"), SavedLook, GGameUserSettingsIni);
        GConfig->GetFloat(TEXT("AegisWar.Interface"), TEXT("ZoomSensitivity"), SavedZoom, GGameUserSettingsIni);
        GConfig->GetBool(TEXT("AegisWar.Interface"), TEXT("InvertX"), SavedX, GGameUserSettingsIni);
        GConfig->GetBool(TEXT("AegisWar.Interface"), TEXT("InvertY"), SavedY, GGameUserSettingsIni);
        PC->GetLocalCameraState() = Camera;
        PC->SaveInterfacePreferences();
        if (!Check(SavedLook == 1.75f && SavedZoom == 0.5f && SavedX && SavedY, TEXT("Camera preference storage failed"))) return;
        PC->ShowInterface(TEXT("Map"));
        PC->ClientEntryRejected_Implementation(FText::FromString(TEXT("UI proof entry failure")));
        if (!Check(!PC->IsInterfaceOpen() && PC->IsMoveInputIgnored() && PC->IsLookInputIgnored(), TEXT("Entry error did not replace modal safely"))) return;
        PC->ToggleMenu();
        if (!Check(!PC->IsInterfaceOpen() && PC->IsMoveInputIgnored(), TEXT("Menu bypassed entry error"))) return;
    }
    else if (Step == Pages.Num()*2+2) PC->ClientOpenFrontend_Implementation();
    else if (Step == Pages.Num()*2+3)
    {
        if (FParse::Param(FCommandLine::Get(), TEXT("WarProofScreenshot")))
            FScreenshotRequest::RequestScreenshot(FPaths::Combine(Folder,TEXT("Entry.png")),true,false);
    }
    else { Finish(true, TEXT("Twelve interface views including UI Settings and Edit UI, entry frame, reference catalogs, GM history and recovery, rejected teleports, controls, panel handoffs and entry isolation passed")); return; }
    ++Step;
    NextStep = Now + 3;
}
