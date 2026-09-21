#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarQuestLogWidget.generated.h"

class SVerticalBox;
class AWarPlayerState;
class AWarQuestNpc;

/** Owner-only quest log and NPC dialogue; every mutation is validated by the server. */
UCLASS()
class AEGISWAR_API UWarQuestLogWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetNpc(AWarQuestNpc* Npc);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
private:
    void Refresh(AWarPlayerState* State);
    TSharedPtr<SVerticalBox> Rows;
    TWeakObjectPtr<AWarPlayerState> DisplayedState;
    int32 DisplayedRevision = INDEX_NONE;
    TWeakObjectPtr<AWarQuestNpc> QuestNpc;
    bool bNpcInteraction = false;
};
