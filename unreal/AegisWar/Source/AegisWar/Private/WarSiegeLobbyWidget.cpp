#include "WarSiegeLobbyWidget.h"
#include "WarSiegeEncounter.h"
#include "WarScenarioSession.h"
#include "Engine/GameInstance.h"
#include "WarSiegeBattlefield.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Kismet/KismetSystemLibrary.h"

TSharedRef<SWidget> UWarSiegeLobbyWidget::RebuildWidget()
{
    SetIsFocusable(true);
    TWeakObjectPtr<AWarPlayerController> PC = Cast<AWarPlayerController>(GetOwningPlayer());
    auto State = [PC]() { return PC.IsValid() ? AWarSiegeEncounter::Find(PC->GetWorld()) : nullptr; };
    auto Content = SNew(SVerticalBox);
    Content->AddSlot().AutoHeight().Padding(0, 0, 0, 18)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 28)).Text(FText::FromString(TEXT("BREACH THE LOWER CITY")))];
    Content->AddSlot().AutoHeight().Padding(0, 0, 0, 12)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",18)).WrapTextAt(800).Text_Lambda([State, PC] {
        const auto* GS = State(); if (!GS) return FText::GetEmpty();
        const auto* PS = PC->GetPlayerState<AWarPlayerState>();
        if (GS->Siege.Phase == EWarSiegePhase::Finished)
        {
            const bool Won = PS && (PS->GetRealm() == EWarRealm::Riftbound) == GS->Siege.bAttackersWon;
            FString Summary = FString::Printf(TEXT("%s — Round %d\nDuration %.0fs | Contested %.0fs | Deaths %d"),
                Won ? TEXT("VICTORY") : TEXT("DEFEAT"), GS->RoundId, GS->Siege.Elapsed, GS->Siege.ContestedSeconds, GS->Deaths);
            const TCHAR* Names[] = { TEXT("Supplies"), TEXT("Checkpoint 1"), TEXT("Checkpoint 2"), TEXT("Gate breach") };
            for (int32 I = 0; I < FMath::Min(4, GS->Siege.MilestoneSeconds.Num()); ++I)
                Summary += FString::Printf(TEXT("\n%s: %.0fs"), Names[I], GS->Siege.MilestoneSeconds[I]);
            return FText::FromString(Summary);
        }
        return FText::FromString(PS && PS->GetRealm() == EWarRealm::Riftbound
            ? TEXT("Riftbound attackers: capture supplies, escort the ram and catapult, and protect their engineers. The ram breaches the gate. Sabotage weakens defenders; claimed objectives raise Riftbound standards.")
            : TEXT("Aegis defenders: contest supplies, stop the engineers and hold the gate until time expires. Protect your emplacement."));
    })];
    Content->AddSlot().AutoHeight().Padding(0, 0, 0, 12)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",18)).AutoWrapText(true)
        .Text_Lambda([State] { const auto* GS = State(); return FText::FromString(GS ? GS->Status : TEXT("Connecting to the siege server...")); })];
    auto Classes = SNew(SHorizontalBox);
    for (uint8 Role = 0; Role < 3; ++Role)
        Classes->AddSlot().FillWidth(1).Padding(3)[SNew(SButton).ContentPadding(FMargin(10,12)).OnClicked_Lambda([PC, State, Role] {
            if (auto* GS = State(); GS && PC.IsValid()) PC->ServerSiegeSelectRole(GS->RoundId, Role);
            return FReply::Handled();
        })[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold",18)).AutoWrapText(true).Text_Lambda([PC,Role] {
            const auto* PS=PC.IsValid() ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
            const TCHAR* Aegis[]={TEXT("TANK\nSunfire Templar"),TEXT("HEALER\nBattle Prelate"),TEXT("DAMAGE\nEmber Arcanist")};
            const TCHAR* Rift[]={TEXT("TANK\nWarbrute"),TEXT("HEALER\nRuin Oracle"),TEXT("DAMAGE\nVoid Magister")};
            return FText::FromString(PS && PS->GetRealm()==EWarRealm::Riftbound ? Rift[Role] : Aegis[Role]);
        })]];
    Content->AddSlot().AutoHeight()[Classes];
    Content->AddSlot().AutoHeight().Padding(0, 12)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",18)).AutoWrapText(true).Text_Lambda([State] {
        const auto* GS = State(); return FText::FromString(GS ? FString::Join(GS->RosterLabels, TEXT("\n")) : FString());
    })];
    Content->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",18)).AutoWrapText(true).Text_Lambda([PC] {
        return FText::FromString(PC.IsValid() ? PC->GetWorldEditMessage() : FString());
    })];
    Content->AddSlot().AutoHeight().Padding(0, 10)[SNew(SButton).ContentPadding(FMargin(12,12))
        .IsEnabled_Lambda([State] { const auto* GS = State(); return GS && GS->bContentReady; })
        .OnClicked_Lambda([PC, State] {
            auto* GS = State(); const auto* PS = PC.IsValid() ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
            if (GS && PS) PC->ServerSiegeReady(GS->RoundId, !GS->ReadyPlayers.Contains(PS->GetPlayerId()));
            return FReply::Handled();
        })[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold",18)).Text_Lambda([PC, State] {
            const auto* GS = State(); const auto* PS = PC.IsValid() ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
            return FText::FromString(GS && PS && GS->ReadyPlayers.Contains(PS->GetPlayerId()) ? TEXT("Cancel ready")
                : GS && GS->Siege.Phase == EWarSiegePhase::Finished ? TEXT("Ready for rematch") : TEXT("Ready"));
        })]];
    Content->AddSlot().AutoHeight()[SNew(SButton).ContentPadding(FMargin(12,10)).OnClicked_Lambda([PC] {
        if (PC.IsValid())
        {
            auto* Session=PC->GetGameInstance()->GetSubsystem<UWarScenarioSession>();
            if (Session && Session->IsRunning()) Session->Leave();
            else UKismetSystemLibrary::QuitGame(PC.Get(), PC.Get(), EQuitPreference::Quit, false);
        }
        return FReply::Handled();
    })[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",18)).Text_Lambda([PC] {
        const auto* Session=PC.IsValid() ? PC->GetGameInstance()->GetSubsystem<UWarScenarioSession>() : nullptr;
        return FText::FromString(Session && Session->IsRunning() ? TEXT("Leave scenario") : TEXT("Leave playtest"));
    })]];
    return SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(FLinearColor(.018f,.014f,.01f,.94f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(SBox).WidthOverride(900).Padding(32)[SNew(SScrollBox)+SScrollBox::Slot()[Content]]];
}
