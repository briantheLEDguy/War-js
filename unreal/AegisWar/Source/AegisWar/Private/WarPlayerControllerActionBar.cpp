#include "WarPlayerController.h"
#include "WarAbilityRuntime.h"
#include "WarAbilityCatalog.h"
#include "WarActionBarWidget.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarContentSubsystem.h"
#include "AbilitySystemComponent.h"
#include "Components/InputComponent.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Misc/ConfigCacheIni.h"

void AWarPlayerController::PlayerTick(float DeltaTime)
{
    Super::PlayerTick(DeltaTime);
    if (!IsLocalController() || !GetLocalPlayer()) return;
    if (bEditingUi && IsMoveInputIgnored()) { bEditingUi = false; SaveActionBars(); }
    const auto* LocalCharacter = Cast<AWarCharacter>(GetPawn());
    const bool bVisible = LocalCharacter && LocalCharacter->IsVisualReady() && !IsMoveInputIgnored()
        && LastEntryFailure.IsEmpty() && !bCharacterEntryPending;
    if (bVisible && !ActionBarWidget)
    {
        ActionBarWidget = CreateWidget<UWarActionBarWidget>(this);
        if (ActionBarWidget) ActionBarWidget->AddToViewport(1);
    }
    if (ActionBarWidget) ActionBarWidget->SetVisibility(bVisible ? ESlateVisibility::SelfHitTestInvisible : ESlateVisibility::Collapsed);
}

void AWarPlayerController::BindActionBarKeys()
{
    InputComponent->BindKey(GetControlKey(TEXT("CycleTarget")), IE_Pressed, this, &AWarPlayerController::CycleCombatTarget);
    InputComponent->BindKey(GetControlKey(TEXT("ActionCursor")), IE_Pressed, this, &AWarPlayerController::ToggleActionCursor);
    for (const auto& Bar : GetActionBars()) for (int32 Button = 0; Button < Bar.Buttons; ++Button)
    {
        const int32 Slot = Bar.Slot(Button);
        const FKey Key = GetControlKey(WarActionBar::Binding(Slot));
        if (!Key.IsValid()) continue;
        FInputKeyBinding Binding(FInputChord(Key), IE_Pressed);
        Binding.KeyDelegate.GetDelegateForManualSet().BindWeakLambda(this, [this, Slot] { ActivateActionSlot(Slot); });
        InputComponent->KeyBindings.Add(MoveTemp(Binding));
    }
}

FName AWarPlayerController::GetActionSlot(int32 Slot)
{
    if (!HasActionSlot(Slot)) return NAME_None;
    const auto* LocalPawn = Cast<AWarCharacter>(GetPawn());
    const FName Career = LocalPawn ? LocalPawn->GetCareerId() : NAME_None;
    if (Career != ActionSlotCareer) { ActionSlots.Reset(); ActionSlotCareer = Career; }
    if (const auto* Found = ActionSlots.Find(Slot)) return *Found;
    const auto* Catalog = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarAbilityCatalog>() : nullptr;
    const auto Kit = Catalog ? Catalog->Kit(Career) : TArray<const FWarAbilityDefinition*>();
    const FString Section = TEXT("AegisWar.ClassActionBar.") + Career.ToString();
    FString Stored;
    bool bStored = !Career.IsNone() && GConfig->GetString(*Section, *WarActionBar::Binding(Slot).ToString(), Stored, GGameUserSettingsIni);
    if (!bStored)
    {
        // Migrate customized slots; the old untouched strike/potion bar becomes the class kit.
        bool bLegacyDefault = true;
        for (int32 Index = 0; Index < 10; ++Index)
        { FString Old; if (GConfig->GetString(TEXT("AegisWar.ActionBar"), *WarActionBar::Binding(Index).ToString(), Old, GGameUserSettingsIni)
            && FName(*Old) != WarActionBar::Default(Index)) bLegacyDefault = false; }
        if (!bLegacyDefault || Slot >= 10) bStored = GConfig->GetString(TEXT("AegisWar.ActionBar"), *WarActionBar::Binding(Slot).ToString(), Stored, GGameUserSettingsIni);
    }
    const FName Action(*Stored);
    const auto* Ability = Catalog ? Catalog->Find(Action,Career) : nullptr;
    const FName Default = Slot >= 0 && Slot < Kit.Num() ? Kit[Slot]->Id : Slot < 10 && Kit.IsEmpty() ? WarActionBar::Default(Slot) : NAME_None;
    // Persisted identities survive assignment removal; unavailable entries remain visibly disabled.
    const FName Result = bStored ? Action : Default;
    if (!Career.IsNone()) ActionSlots.Add(Slot, Result);
    return Result;
}

bool AWarPlayerController::SetActionSlot(int32 Slot, FName Action)
{
    if (!HasActionSlot(Slot) || !GetAvailableActions().Contains(Action)) return false;
    GetActionSlot(Slot);
    ActionSlots.Add(Slot, Action);
    const FString Section = ActionSlotCareer.IsNone() ? TEXT("AegisWar.ActionBar") : TEXT("AegisWar.ClassActionBar.") + ActionSlotCareer.ToString();
    GConfig->SetString(*Section, *WarActionBar::Binding(Slot).ToString(), *Action.ToString(), GGameUserSettingsIni);
    GConfig->Flush(false, GGameUserSettingsIni);
    return true;
}

FString AWarPlayerController::GetActionLabel(FName Action) const
{
    const auto* Catalog = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarAbilityCatalog>() : nullptr;
    const auto* LocalPawn=Cast<AWarCharacter>(GetPawn());
    const auto* Ability = Catalog && LocalPawn ? Catalog->Find(Action,LocalPawn->GetCareerId()) : nullptr;
    return Ability ? Ability->Name : WarActionBar::IsSupported(Action) ? WarActionBar::Label(Action) : Action.ToString()+TEXT(" (unassigned)");
}
TArray<FName> AWarPlayerController::GetAvailableActions() const
{
    TArray<FName> Actions{NAME_None, TEXT("strike"), TEXT("health_potion"), TEXT("mana_potion")};
    const auto* Catalog = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarAbilityCatalog>() : nullptr;
    const auto* LocalPawn = Cast<AWarCharacter>(GetPawn());
    if (Catalog && LocalPawn) for (const auto* A : Catalog->Kit(LocalPawn->GetCareerId())) Actions.Add(A->Id);
    return Actions;
}
FString AWarPlayerController::GetClassAbilityStatus() const
{
    const auto* State = GetPlayerState<AWarPlayerState>();
    return State ? State->GetClassAbilities()->Description() : FString();
}

bool AWarPlayerController::IsCombatTarget(const AActor* Target) const
{
    const auto* Self = Cast<AWarCharacter>(GetPawn());
    const auto* State = GetPlayerState<AWarPlayerState>();
    if (!Self || !State || !IsValid(Target) || Target == Self || Target->GetWorld() != GetWorld()
        || Target->IsHidden() || FVector::DistSquared(Self->GetActorLocation(), Target->GetActorLocation()) > FMath::Square(5000.0)) return false;
    if (const auto* Enemy = Cast<AWarEnemy>(Target))
        return Enemy->IsContentReady() && !Enemy->IsDead() && Enemy->ZoneId == State->GetCurrentZone();
    const auto* TargetCharacter = Cast<AWarCharacter>(Target);
    const auto* Other = TargetCharacter ? TargetCharacter->GetPlayerState<AWarPlayerState>() : nullptr;
    return Other && TargetCharacter->IsVisualReady() && !TargetCharacter->IsDead()
        && Other->GetCurrentZone() == State->GetCurrentZone() && State->GetRealm() != EWarRealm::None
        && Other->GetRealm() != EWarRealm::None;
}

AActor* AWarPlayerController::GetCombatTarget() const
{
    return IsCombatTarget(CombatTarget.Get()) ? CombatTarget.Get() : nullptr;
}

void AWarPlayerController::CycleCombatTarget()
{
    if (IsMoveInputIgnored() || !GetPawn()) return;
    TArray<AActor*> Targets;
    for (TActorIterator<APawn> It(GetWorld()); It; ++It)
        if (IsCombatTarget(*It) && LineOfSightTo(*It)) Targets.Add(*It);
    Targets.Sort([this](const AActor& A, const AActor& B) {
        const double DA = FVector::DistSquared(A.GetActorLocation(), GetPawn()->GetActorLocation());
        const double DB = FVector::DistSquared(B.GetActorLocation(), GetPawn()->GetActorLocation());
        return DA == DB ? A.GetUniqueID() < B.GetUniqueID() : DA < DB;
    });
    CombatTarget = Targets.IsEmpty() ? nullptr : Targets[(Targets.IndexOfByKey(GetCombatTarget()) + 1) % Targets.Num()];
}

FString AWarPlayerController::GetCombatTargetLabel() const
{
    const auto* Target = GetCombatTarget();
    if (!Target) return TEXT("No target - ") + GetControlKey(TEXT("CycleTarget")).GetDisplayName().ToString() + TEXT(" selects a nearby combatant");
    FString Name; float Health = 0, Max = 0;
    if (const auto* Enemy = Cast<AWarEnemy>(Target))
    { Name = Enemy->GetDefinition().Name; Health = Enemy->GetHealth(); Max = Enemy->GetDefinition().MaxHealth; }
    else if (const auto* TargetPlayer = Cast<AWarCharacter>(Target))
        if (const auto* State = TargetPlayer->GetPlayerState<AWarPlayerState>())
        { Name = State->GetPlayerName(); if (const auto* Stats = State->GetAttributes()) { Health = Stats->GetHealth(); Max = Stats->GetMaxHealth(); } }
    return FString::Printf(TEXT("%s   %.0f / %.0f HP   |   %.1f m"), *Name, Health, Max, FVector::Distance(Target->GetActorLocation(), GetPawn()->GetActorLocation()) / 100);
}

void AWarPlayerController::ToggleActionCursor()
{
    if (bEditingUi || IsMoveInputIgnored() || !GetPawn() || !LastEntryFailure.IsEmpty()) return;
    bShowMouseCursor = !bShowMouseCursor;
    if (bShowMouseCursor) { FInputModeGameAndUI Mode; Mode.SetHideCursorDuringCapture(false); SetInputMode(Mode); }
    else SetInputMode(FInputModeGameOnly());
}

FWarActionSlotView AWarPlayerController::GetActionSlotView(int32 Slot)
{
    FWarActionSlotView View;
    const FName Action = GetActionSlot(Slot);
    View.Label = GetActionLabel(Action);
    const auto* Catalog = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarAbilityCatalog>() : nullptr;
    const auto* Self = Cast<AWarCharacter>(GetPawn());
    const auto* Ability = Catalog && Self ? Catalog->Find(Action,Self->GetCareerId()) : nullptr;
    const auto* State = GetPlayerState<AWarPlayerState>();
    const auto* Stats = State ? State->GetAttributes() : nullptr;
    if (!Self || !Stats || !Self->IsVisualReady() || Self->IsDead() || IsMoveInputIgnored())
    { View.Detail = TEXT("Unavailable while defeated, loading or in a menu."); return View; }
    if (Ability)
    {
        const auto* Runtime = State->GetClassAbilities(); FString Reason;
        View.Cooldown = Runtime->Cooldown(Action);
        View.Detail = Ability->Summary + FString::Printf(TEXT("\nLevel %d | %.0f mana | %.1fs cooldown | %.1fm range"),
            Ability->UnlockLevel, Ability->Mana, Ability->Cooldown, Ability->Range / 100);
        if (Ability->Cost > 0) View.Detail += FString::Printf(TEXT(" | %.0f %s"), Ability->Cost, *Ability->ResourceLabel);
        View.bAvailable = Runtime->CanActivate(*Ability, GetCombatTarget(), Reason, false);
        if (!Reason.IsEmpty()) View.Detail += TEXT("\n") + Reason;
        View.Footer = !Ability->UnavailableReason.IsEmpty() ? TEXT("Unavailable")
            : State->GetCombatLevel() < Ability->UnlockLevel ? FString::Printf(TEXT("Level %d"), Ability->UnlockLevel)
            : FString::Printf(TEXT("%.0f mana"), Ability->Mana);
    }
    else if (Action == TEXT("strike"))
    {
        View.Detail = TEXT("Basic strike: 10 mana, 3 m range, 2 s cooldown. The server validates the target and damage.");
        View.Footer = TEXT("10 mana");
        if (const auto* ASC = State->GetAbilitySystemComponent())
        {
            const FGameplayTag Tag = FGameplayTag::RequestGameplayTag(TEXT("War.Cooldown.DevelopmentStrike"), false);
            if (Tag.IsValid())
                for (float Remaining : ASC->GetActiveEffectsTimeRemaining(FGameplayEffectQuery::MakeQuery_MatchAnyOwningTags(FGameplayTagContainer(Tag))))
                    View.Cooldown = FMath::Max(View.Cooldown, Remaining);
        }
        const AActor* Target = GetCombatTarget();
        View.bAvailable = Target && !Self->IsActionPlaying() && !State->GetClassAbilities()->IsBusy() && View.Cooldown <= 0 && Stats->GetMana() >= WarValidation::StrikeManaCost
            && FVector::DistSquared(Target->GetActorLocation(), Self->GetActorLocation()) <= FMath::Square(WarValidation::StrikeRangeCm)
            && LineOfSightTo(Target) && Self->CanAbilityTarget(Target,WarValidation::StrikeRangeCm);
        if (!Target) View.Detail += TEXT(" Select a hostile target first.");
        else if (!View.bAvailable) View.Detail += TEXT(" Requires enough mana, a clear path and melee range; wait for any cooldown.");
    }
    else if (Action == TEXT("health_potion") || Action == TEXT("mana_potion"))
    {
        const auto* Content = GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
        for (const auto& Item : State->GetInventory().Items)
        {
            float Health = 0, Mana = 0;
            if (Item.Quantity > 0 && Item.EquipSlot.IsNone() && Content && Content->GetConsumableEffect(Item.Key, Health, Mana)
                && (Action == TEXT("health_potion") ? Health > 0 : Mana > 0)) View.Count += Item.Quantity;
        }
        View.bAvailable = View.Count > 0 && (Action == TEXT("health_potion") ? Stats->GetHealth() < Stats->GetMaxHealth() : Stats->GetMana() < Stats->GetMaxMana());
        View.Detail = TEXT("Uses the first matching potion in bag-slot order. Requires a missing resource; quantity comes from your inventory.");
        View.Footer = FString::Printf(TEXT("x%d"), View.Count);
    }
    else View.Detail = Action.IsNone() ? TEXT("Empty slot. Assign a class ability or potion in Menu > UI Settings > Configure button.") : TEXT("This assignment was removed. The saved hotbar identity is retained; choose an available class ability.");
    return View;
}

FString AWarPlayerController::GetActionMessage() const
{
    if (const auto* State = GetPlayerState<AWarPlayerState>())
        if (!State->GetClassAbilities()->GetMessage().IsEmpty()) return State->GetClassAbilities()->GetMessage();
    return GetWorld()->GetTimeSeconds() < ActionMessageUntil ? ActionMessage : FString();
}

void AWarPlayerController::ActivateActionSlot(int32 Slot)
{
    if (!HasActionSlot(Slot) || bEditingUi || IsMoveInputIgnored() || !LastEntryFailure.IsEmpty()) return;
    const auto View = GetActionSlotView(Slot);
    if (!View.bAvailable) { ActionMessage = View.Detail; ActionMessageUntil = GetWorld()->GetTimeSeconds() + 4; return; }
    const FName Action = GetActionSlot(Slot);
    const auto* Catalog = GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    const auto* LocalPawn=Cast<AWarCharacter>(GetPawn());
    if (Catalog && LocalPawn && Catalog->Find(Action,LocalPawn->GetCareerId()))
    {
        FVector Ground=FVector::ZeroVector;
        if (Catalog->Find(Action,LocalPawn->GetCareerId())->TargetKind==TEXT("ground"))
        { FHitResult Hit; if (!GetHitResultUnderCursor(ECC_Visibility,false,Hit)) { ActionMessage=TEXT("Point at a loaded ground surface."); ActionMessageUntil=GetWorld()->GetTimeSeconds()+4; return; } Ground=Hit.ImpactPoint; }
        if (auto* State=GetPlayerState<AWarPlayerState>()) State->GetClassAbilities()->ServerActivateVersioned(Action,GetCombatTarget(),Catalog->GetVersion(),Ground); return;
    }
    if (Action == TEXT("strike"))
    { if (auto* Self = Cast<AWarCharacter>(GetPawn())) Self->RequestTargetStrike(GetCombatTarget()); return; }
    auto* State = GetPlayerState<AWarPlayerState>();
    const auto* Content = GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
    if (!State || !Content) return;
    int32 BagSlot = MAX_int32;
    for (const auto& Item : State->GetInventory().Items)
    {
        float Health = 0, Mana = 0;
        if (Item.Quantity > 0 && Item.EquipSlot.IsNone() && Content->GetConsumableEffect(Item.Key, Health, Mana)
            && (Action == TEXT("health_potion") ? Health > 0 : Mana > 0)) BagSlot = FMath::Min(BagSlot, Item.Slot);
    }
    if (BagSlot != MAX_int32) State->ServerUseConsumable(State->GetInventory().Revision, BagSlot);
}
