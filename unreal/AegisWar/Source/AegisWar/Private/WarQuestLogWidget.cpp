#include "WarQuestLogWidget.h"
#include "WarContentSubsystem.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarQuestNpc.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"

void UWarQuestLogWidget::SetNpc(AWarQuestNpc* Npc)
{
    QuestNpc = Npc;
    bNpcInteraction = Npc != nullptr;
    DisplayedRevision = INDEX_NONE;
    Refresh(GetOwningPlayerState<AWarPlayerState>());
}

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
    if (bNpcInteraction)
    {
        FString Name, Error;
        if (!QuestNpc.IsValid() || !QuestNpc->ResolveInteraction(GetOwningPlayerPawn(), Name, Error))
        { Text(TEXT("This character is unavailable or too far away. Close this panel and approach again.")); return; }
        Text(Name, true);
        Rows->AddSlot().AutoHeight().Padding(0, 0, 0, 8)
            [SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular", 17))
                .Text_Lambda([WeakState = TWeakObjectPtr<AWarPlayerState>(State)] {
                return WeakState.IsValid() ? WeakState->GetInventoryMessage() : FText::GetEmpty();
            })];
        const FName Realm = State->GetRealm() == EWarRealm::Aegis ? FName(TEXT("aegis")) : FName(TEXT("riftbound"));
        bool bAny = false;
        for (const auto& Quest : Content->GetQuestsForNpc(QuestNpc->ZoneId, QuestNpc->NpcId))
        {
            if (!Quest.Realm.IsNone() && Quest.Realm != Realm) continue;
            const auto* Progress = Quests.FindByPredicate([&](const auto& Row) { return Row.Id == Quest.Id; });
            auto Preview = Quests;
            const bool bOffer = Quest.GiverNpcId == QuestNpc->NpcId
                && WarQuests::Accept(Quest, Realm, QuestNpc->ZoneId, State->GetInventory().CharacterProgression.Level, Preview, Error);
            const bool bTurnIn = Quest.TurninNpcId == QuestNpc->NpcId && Progress && Progress->Status == TEXT("ready_to_turn_in");
            const bool bActive = Quest.GiverNpcId == QuestNpc->NpcId && Progress && Progress->Status == TEXT("active");
            if (!bOffer && !bTurnIn && !bActive) continue;
            bAny = true;
            Text(Quest.Title, true); Text(Quest.Description);
            for (const auto& Objective : Quest.Objectives)
                Text(FString::Printf(TEXT("%s: %d / %d"), *Objective.Description, Progress ? Progress->GetCount(Objective.Id) : 0, Objective.Required));
            Text(FString::Printf(TEXT("Reward: %d XP, %d gold"), Quest.Xp, Quest.Gold));
            for (const auto& Reward : Quest.Rewards)
            {
                FString Item = FString::Printf(TEXT("%d x %s"), Reward.Item.Quantity, *Content->GetItemDisplayName(Reward.Item.Key).ToString());
                if (Reward.bRollStrength) Item += FString::Printf(TEXT(" (Strength +%d to +%d)"), Reward.MinimumStrength, Reward.MaximumStrength);
                Text(Item);
            }
            if (bActive) { Text(TEXT("In progress")); continue; }
            FString Blocker;
            if (bTurnIn)
            {
                TArray<FWarInventoryItem> Rewards;
                FWarInventorySnapshot Next;
                auto ProgressPreview = Quests;
                if (WarQuests::ResolveRewards(Quest, [] { return 0.0; }, Rewards, Blocker))
                    WarQuests::TurnIn(Quest, Realm, QuestNpc->ZoneId, Rewards, State->GetInventory(), ProgressPreview, Next, Blocker);
                if (!Blocker.IsEmpty()) Text(Blocker);
            }
            Rows->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
                [SNew(SButton).IsEnabled_Lambda([WeakNpc = QuestNpc, WeakState = TWeakObjectPtr<AWarPlayerState>(State), bBlocked = !Blocker.IsEmpty()] {
                    FString NpcName, Failure;
                    return !bBlocked && WeakNpc.IsValid() && WeakState.IsValid() && WeakNpc->ResolveInteraction(WeakState->GetPawn(), NpcName, Failure);
                }).OnClicked_Lambda([WeakNpc = QuestNpc, WeakState = TWeakObjectPtr<AWarPlayerState>(State), Id = Quest.Id,
                                    bTurnIn, Revision = DisplayedRevision] {
                    if (WeakNpc.IsValid() && WeakState.IsValid()) WeakState->ServerInteractQuest(WeakNpc.Get(), Id, bTurnIn, Revision);
                    return FReply::Handled();
                })[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 20))
                    .Text(FText::FromString(bTurnIn ? TEXT("Complete quest") : TEXT("Accept quest")))]];
        }
        if (!bAny) Text(TEXT("No quests are available here for this character."));
        return;
    }
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
