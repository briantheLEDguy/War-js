#include "WarInterfaceProof.h"
#include "WarPlayerController.h"
#include "SWarCombatUiEditor.h"
#include "Framework/Application/SlateApplication.h"
#include "Layout/WidgetPath.h"
#include "Widgets/SWindow.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SEditableText.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/ConfigCacheIni.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "Engine/World.h"

namespace
{
    TSharedPtr<SWidget> Find(const TSharedRef<SWidget>& W,const FString& Type,FName Tag=NAME_None)
    {
        if (W->GetTypeAsString().StartsWith(Type) && (Tag.IsNone() || W->GetTag()==Tag)) return W;
        auto* Children=W->GetChildren();
        for (int I=0;Children && I<Children->Num();++I) if (auto Match=Find(Children->GetChildAt(I),Type,Tag)) return Match;
        return nullptr;
    }
    TSharedPtr<SWidget> Find(const FString& Type,FName Tag=NAME_None)
    { for (const auto& Window:FSlateApplication::Get().GetTopLevelWindows()) if (auto W=Find(Window,Type,Tag)) return W; return nullptr; }
    bool Drag(const TSharedPtr<SWidget>& W,FVector2D Delta)
    {
        if (!W) return false;
        auto& Slate=FSlateApplication::Get(); FWidgetPath Path;
        if (!Slate.GeneratePathToWidgetUnchecked(W.ToSharedRef(),Path)) return false;
        TArray<FWidgetAndPointer> P; for (int I=0;I<Path.Widgets.Num();++I) P.Emplace(Path.Widgets[I]); Path=FWidgetPath(MakeArrayView(P));
        const FVector2D Start=W->GetCachedGeometry().LocalToAbsolute(W->GetCachedGeometry().GetLocalSize()*.5),End=Start+Delta;
        const uint32 Pointer=FSlateApplication::CursorPointerIndex; const TSet<FKey> Pressed{EKeys::LeftMouseButton};
        Slate.RoutePointerDownEvent(Path,FPointerEvent(Pointer,Start,Start,Pressed,EKeys::LeftMouseButton,0,FModifierKeysState()));
        const FVector2D Middle=Start+Delta*.5;
        Slate.RoutePointerMoveEvent(Path,FPointerEvent(Pointer,Middle,Start,Pressed,EKeys::Invalid,0,FModifierKeysState()),false);
        Slate.RoutePointerMoveEvent(Path,FPointerEvent(Pointer,End,Middle,Pressed,EKeys::Invalid,0,FModifierKeysState()),false);
        Slate.RoutePointerUpEvent(Path,FPointerEvent(Pointer,End,End,{},EKeys::LeftMouseButton,0,FModifierKeysState()));
        return !W->HasMouseCapture();
    }
}
void UWarInterfaceProof::TickCombatUi(double Now)
{
    FString Run; FGuid Id;
    if (!FParse::Value(FCommandLine::Get(),TEXT("WarCombatUiRun="),Run) || !FGuid::Parse(Run,Id)) { Finish(false,TEXT("Combat UI proof needs isolated run id")); return; }
    const FString Folder=FPaths::ProjectSavedDir()/TEXT("CombatUiProof")/Id.ToString(EGuidFormats::Digits);
    IFileManager::Get().MakeDirectory(*Folder,true);
    auto* PC=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController()); if (!PC) return;
    const auto Check=[&](bool Passed,const TCHAR* Detail) { if (!Passed) { FFileHelper::SaveStringToFile(Detail,*(Folder/TEXT("failure.txt"))); Finish(false,Detail); } return Passed; };
    auto Editor=StaticCastSharedPtr<SWarCombatUiEditor>(Find(TEXT("SWarCombatUiEditor")));
    if (FParse::Param(FCommandLine::Get(),TEXT("WarCombatUiReload")))
    {
        // A second process uses the first run's isolated INI without resetting preferences.
        const auto& Saved=PC->GetCombatUiSettings();
        if (!Check(Saved.Styles[2].Scale==2 && Saved.Styles[2].Rise==128 && Saved.Styles[2].Burst==8
            && !Saved.Styles[4].Visible && Saved.Styles[4].X!=0
            && Saved.Styles[1].Colors[0].ToFColorSRGB()==FColor::FromHex(TEXT("22CC88FF"))
            && Saved.Styles[11].Colors[0]==Saved.Styles[1].Colors[0],TEXT("Fresh process did not restore combat UI preferences"))) return;
        if (Step==0) PC->SetEditingUi(true);
        else if (Step==1)
        {
            if (!Check(Editor.IsValid(),TEXT("Restart editor did not open"))) return;
            Editor->Select(4); Editor->Preview.Replay(2); Editor->Preview.Advance(.3f,Saved); Editor->Preview.Paused=true;
            FScreenshotRequest::RequestScreenshot(Folder/TEXT("restart.png"),true,false);
        }
        else
        {
            PC->SetEditingUi(false);
            if (!Check(PC->IsInterfaceOpen(),TEXT("Restart Done flow failed"))) return;
            FFileHelper::SaveStringToFile(TEXT("{\"passed\":true,\"freshProcess\":true,\"customMotion\":true,\"hiddenPosition\":true,\"copiedColors\":true}"),*(Folder/TEXT("restart.json")));
            Finish(true,TEXT("Combat UI preferences restored in a fresh game process")); return;
        }
        ++Step; NextStep=Now+1; return;
    }
    if (Step==0) { BuilderObjectCount=PC->GetCombatNotices().Num(); PC->ResetCombatUi(); PC->SetEditingUi(true); }
    else if (Step==1)
    {
        if (!Check(Editor.IsValid() && PC->IsEditingUi() && PC->IsMoveInputIgnored() && PC->IsLookInputIgnored(),TEXT("Editor/input lock failed"))) return;
        Editor->Preview.Replay(0); Editor->Preview.Advance(.3f,PC->GetCombatUiSettings()); Editor->Preview.Paused=true;
        FScreenshotRequest::RequestScreenshot(Folder/TEXT("default.png"),true,false);
    }
    else if (Step==2)
    {
        const float Before=PC->GetCombatUiSettings().Styles[1].X;
        if (!Check(Drag(Find(TEXT("SWarCombatHandle"),TEXT("CombatUi.1")),FVector2D(28,-12)) && Editor->Selected==1 && PC->GetCombatUiSettings().Styles[1].X!=Before,TEXT("Preview selection/drag failed"))) return;
        FWarCombatUiSettings Saved; Saved.Load(GGameUserSettingsIni);
        if (!Check(Saved.Styles[1].X==PC->GetCombatUiSettings().Styles[1].X,TEXT("Drag release autosave failed"))) return;
        if (!PC->GetActionBars().IsEmpty())
        {
            const auto Bar=PC->GetActionBars()[0];
            if (!Check(Drag(Find(TEXT("SWarBarHandle")),FVector2D(30,-15)) && PC->GetActionBars()[0].Position!=Bar.Position,TEXT("Action-bar editing regression"))) return;
        }
        auto S=PC->GetCombatUiSettings().Styles[4]; S.Visible=false; PC->SetCombatUiStyle(4,S); Editor->Select(4);
    }
    else if (Step==3)
    {
        if (!Check(Drag(Find(TEXT("SWarCombatHandle"),TEXT("CombatUi.4")),FVector2D(18,0)) && !PC->GetCombatUiSettings().Styles[4].Visible && PC->GetCombatUiSettings().Styles[4].X!=0,TEXT("Hidden element drag recovery failed"))) return;
        FScreenshotRequest::RequestScreenshot(Folder/TEXT("hidden.png"),true,false);
    }
    else if (Step==4) Editor->Select(1);
    else if (Step==5)
    {
        const float Before=PC->GetCombatUiSettings().Styles[1].X;
        if (!Check(Drag(Find(TEXT("SSpinBox"),TEXT("X")),FVector2D(24,0)) && PC->GetCombatUiSettings().Styles[1].X!=Before,TEXT("Numeric control interaction failed"))) return;
        auto Hex=StaticCastSharedPtr<SEditableTextBox>(Find(TEXT("SEditableTextBox"),TEXT("Color0")));
        if (!Check(Hex.IsValid(),TEXT("Color control missing"))) return;
        Hex->SetText(FText::FromString(TEXT("22CC88FF")));
        auto Text=Find(Hex.ToSharedRef(),TEXT("SEditableText"));
        if (!Check(Text.IsValid(),TEXT("Color input missing"))) return;
        FSlateApplication::Get().SetKeyboardFocus(Text,EFocusCause::SetDirectly);
        FSlateApplication::Get().ProcessKeyDownEvent(FKeyEvent(EKeys::Enter,FModifierKeysState(),0,false,0,0));
        if (!Check(PC->GetCombatUiSettings().Styles[1].Colors[0].ToFColorSRGB()==FColor::FromHex(TEXT("22CC88FF")),TEXT("Hex commit failed"))) return;
        PC->CopyCombatUiSide(1);
        auto S=PC->GetCombatUiSettings().Styles[2]; S.Scale=2; S.Font=36; S.Rise=128; S.Burst=8; PC->SetCombatUiStyle(2,S);
        Editor->Select(2); Editor->Preview.Replay(1); Editor->Preview.Advance(.15f,PC->GetCombatUiSettings()); Editor->Preview.Paused=true;
    }
    else if (Step==6)
    {
        FScreenshotRequest::RequestScreenshot(Folder/TEXT("extreme.png"),true,false);
        // Initial character restoration can already have produced real healing feedback.
        if (!Check(PC->GetCombatNotices().Num()==BuilderObjectCount && PC->GetFloatingCombatNumbers().IsEmpty(),TEXT("Mock events escaped preview"))) return;
    }
    else if (Step==7)
    {
        FSlateApplication::Get().ProcessKeyDownEvent(FKeyEvent(EKeys::Escape,FModifierKeysState(),0,false,0,0));
        if (!Check(!PC->IsEditingUi() && PC->IsInterfaceOpen(),TEXT("Escape did not return to settings"))) return;
        PC->SetEditingUi(true);
    }
    else if (Step==8)
    {
        FWarCombatUiSettings Saved; Saved.Load(GGameUserSettingsIni);
        if (!Check(PC->IsEditingUi() && Saved.Styles[2].Scale==2 && Saved.Styles[1].Colors[0]==Saved.Styles[11].Colors[0],TEXT("Reopen persistence/copy failed"))) return;
        PC->SetEditingUi(false); if (!Check(PC->IsInterfaceOpen(),TEXT("Done flow failed"))) return;
        PC->SetEditingUi(true); PC->CloseAllPanels();
        if (!Check(!PC->IsEditingUi() && !PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored(),TEXT("Interruption input cleanup failed"))) return;
        FFileHelper::SaveStringToFile(TEXT("{\"passed\":true,\"pointerDrag\":true,\"hiddenDrag\":true,\"numericAndHex\":true,\"autosave\":true,\"actionBars\":true,\"escapeDoneInterruption\":true,\"networkAcceptance\":false}"),*(Folder/TEXT("report.json")));
        Finish(true,TEXT("Combat UI interactions and screenshot capture complete")); return;
    }
    ++Step; NextStep=Now+1;
}
