#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarResourceNode.h"
#include "Misc/DateTime.h"

bool AWarPlayerState::GatherResource(const AWarResourceNode* Node, const int32 ExpectedRevision, FString& Error)
{
    if (!HasAuthority() || ExpectedRevision != Inventory.Revision || !CanPerformInventoryAction() || !IsValid(Node))
    { Error = TEXT("Gathering is unavailable or inventory changed."); return false; }
    FWarResourceDefinition Definition;
    if (!Node->ResolveInteraction(GetPawn(), Definition, Error)) return false;
    const int64 NowMs = (FDateTime::UtcNow() - FDateTime(1970, 1, 1)).GetTicks() / ETimespan::TicksPerMillisecond;
    FRandomStream Random(GetTypeHash(FGuid::NewGuid()));
    if (!WarGathering::Gather(Inventory, Definition, NowMs, Random, Error)) return false;
    ForceNetUpdate(); return true;
}
void AWarPlayerState::ServerGatherResource_Implementation(AWarResourceNode* Node, const int32 ExpectedRevision)
{
    FString Error; const bool Accepted = GatherResource(Node, ExpectedRevision, Error); ClientInventoryResult(Accepted, Error);
}
