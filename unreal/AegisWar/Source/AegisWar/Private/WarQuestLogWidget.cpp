#include "WarQuestLogWidget.h"
#include "WarContentSubsystem.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"

TSharedRef<SWidget> UWarQuestLogWidget::RebuildWidget()
{
    DisplayedRevision = INDEX_NONE;
    return SNew(SBox).WidthOverride(540.f).HeightOverride(650.f)
        [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).Padding(16.f)
            .BorderBackgroundColor(FLinearColor(0.025f, 0.03f, 0.045f, 1.f))
            [SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
                [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 26))
                    .Text(NSLOCTEXT("AegisWar", "QuestLog", "Quest Log"))]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
                [SNew(SButton)
                    .OnClicked_Lambda([WeakThis = TWeakObjectPtr<UWarQuestLogWidget>(this)] {
                        if (WeakThis.IsValid())
                            if (auto* Controller = Cast<AWarPlayerController>(WeakThis->GetOwningPlayer())) Controller->ToggleQuestLog();
                        return FReply::Handled();
                    })[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 20))
                        .Text(NSLOCTEXT("AegisWar", "CloseQuestLog", "Close quest log"))]]
                + SVerticalBox::Slot().FillHeight(1.f)
                [SNew(SScrollBox) + SScrollBox::Slot()[SAssignNew(Rows, SVerticalBox)]]]];
}

void UWarQuestLogWidget::NativeTick(const FGeometry& Geometry, const float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    auto* State = GetOwningPlayerState<AWarPlayerState>();
    if (Rows && (DisplayedState != State || (State && DisplayedRevision != State->GetInventory().Revision))) Refresh(State);
}

void UWarQuestLogWidget::ReleaseSlateResources(const bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    Rows.Reset();
    DisplayedState.Reset();
    DisplayedRevision = INDEX_NONE;
}

void UWarQuestLogWidget::Refresh(AWarPlayerState* State)
{
    if (!Rows) return;
    Rows->ClearChildren();
    DisplayedState = State;
    DisplayedRevision = State ? State->GetInventory().Revision : INDEX_NONE;
    const auto Text = [this](const FString& Value, bool bHeading = false) {
        Rows->AddSlot().AutoHeight().Padding(0, 0, 0, 8)
            [SNew(STextBlock).AutoWrapText(true)
                .Font(FCoreStyle::GetDefaultFontStyle(bHeading ? "Bold" : "Regular", bHeading ? 20 : 17))
                .Text(FText::FromString(Value))];
    };
    if (!State) { Text(TEXT("Waiting for character data.")); return; }
    auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    if (!Content || !Content->IsContentReady()) { Text(TEXT("Quest details are unavailable. Please reconnect.")); return; }
    const auto& Quests = State->GetInventory().Quests;
    for (const bool bCompleted : {false, true})
    {
        int32 Count = 0;
        for (const auto& Progress : Quests) if ((Progress.Status == TEXT("completed")) == bCompleted) ++Count;
        Text(FString::Printf(TEXT("%s (%d)"), bCompleted ? TEXT("Completed") : TEXT("Active"), Count), true);
        if (!bCompleted && Count == 0) Text(TEXT("No active quests."));
        for (const auto& Progress : Quests)
        {
            if ((Progress.Status == TEXT("completed")) != bCompleted) continue;
            FWarQuestDefinition Quest; FString Error;
            if (!Content->GetQuest(Progress.Id, Quest, Error))
            { Text(TEXT("Quest details unavailable: ") + Progress.Id.ToString()); continue; }
            Text(Quest.Title + (Progress.Status == TEXT("ready_to_turn_in") ? TEXT(" - Ready to turn in") : TEXT("")), true);
            Text(Quest.Description);
            for (const auto& Objective : Quest.Objectives)
                Text(FString::Printf(TEXT("%s: %d / %d"), *Objective.Description, Progress.GetCount(Objective.Id), Objective.Required));
            FString Rewards = FString::Printf(TEXT("Reward: %d XP, %d gold"), Quest.Xp, Quest.Gold);
            for (const auto& Reward : Quest.Rewards)
            {
                Rewards += FString::Printf(TEXT("\n%d x %s"), Reward.Item.Quantity, *Content->GetItemDisplayName(Reward.Item.Key).ToString());
                if (Reward.bRollStrength) Rewards += FString::Printf(TEXT(" (Strength +%d to +%d)"), Reward.MinimumStrength, Reward.MaximumStrength);
            }
            Text(Rewards);
        }
    }
}
