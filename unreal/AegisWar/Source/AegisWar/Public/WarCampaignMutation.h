#pragma once
#include "CoreMinimal.h"
#include "WarInventorySnapshot.h"
#include "Dom/JsonObject.h"
class AWarPlayerState;

/** Nested normal-character mutations commit one complete document before reporting success. */
class AEGISWAR_API FWarCampaignMutation
{
public:
    explicit FWarCampaignMutation(AWarPlayerState* Player);
    ~FWarCampaignMutation();
    bool Ready(FString& Error) const;
    bool Commit(FString& Error);
private:
    AWarPlayerState* Player = nullptr;
    bool bOuter = false, bCommitted = false;
    FWarInventorySnapshot Inventory;
    TSharedPtr<FJsonObject> Runtime;
    FString CaptureError;
    float MaxHealth = 0, MaxMana = 0;
};
