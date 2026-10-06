#include "WarCampaignMutation.h"
#include "WarPlayerState.h"
#include "WarCampaignSiegeSubsystem.h"
#include "WarPlayerController.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"

FWarCampaignMutation::FWarCampaignMutation(AWarPlayerState* InPlayer)
{
    auto* Bridge = InPlayer && InPlayer->GetWorld() ? InPlayer->GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>() : nullptr;
    if (!Bridge || !Bridge->JournalsMutations(InPlayer)) return;
    Player = InPlayer; bOuter = Player->CampaignMutationDepth++ == 0;
    if (bOuter)
    {
        Inventory = Player->Inventory; Runtime = Player->CaptureCampaignState(CaptureError);
        MaxHealth = Player->Attributes->GetMaxHealth(); MaxMana = Player->Attributes->GetMaxMana();
    }
    else Player->CaptureCampaignState(CaptureError);
    if (bOuter && !Runtime && CaptureError.IsEmpty()) CaptureError=TEXT("The complete campaign rollback state is unavailable.");
}
FWarCampaignMutation::~FWarCampaignMutation()
{
    if (!Player) return;
    --Player->CampaignMutationDepth;
    if (!bOuter || bCommitted || !Runtime) return;
    Player->Inventory = Inventory;
    Player->AbilitySystem->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),MaxHealth);
    Player->AbilitySystem->SetNumericAttributeBase(UWarAttributeSet::GetMaxManaAttribute(),MaxMana);
    FString RestoreError;
    if (!Player->RestoreCampaignState(Runtime,RestoreError)) Player->SetScenarioTransferPending(true);
    Player->ForceNetUpdate();
    // Transaction rollback preserves defeat; normal scenario return deliberately clamps to living pools.
    Player->AbilitySystem->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),Runtime->GetNumberField(TEXT("health")));
}
bool FWarCampaignMutation::Commit(FString& Error)
{
    if (!Ready(Error)) return false;
    if (!Player || !bOuter) { bCommitted = true; return true; }
    auto* Bridge = Player->GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>();
    if (!Bridge || !Bridge->CommitMutation(Cast<AWarPlayerController>(Player->GetOwner()),Error)) return false;
    bCommitted = true; return true;
}
bool FWarCampaignMutation::Ready(FString& Error) const
{ if (!CaptureError.IsEmpty()) { Error=CaptureError; return false; } return true; }
