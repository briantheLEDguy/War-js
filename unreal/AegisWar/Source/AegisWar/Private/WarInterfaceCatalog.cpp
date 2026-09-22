#include "WarInterfaceCatalog.h"
#include "Dom/JsonObject.h"

namespace
{
    FString String(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key)
    { FString Value; if (Object) Object->TryGetStringField(Key, Value); return Value; }
    double Number(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, double Default = 0)
    { double Value; return Object && Object->TryGetNumberField(Key, Value) && FMath::IsFinite(Value) ? Value : Default; }
    TArray<TSharedPtr<FJsonValue>> Array(const TSharedPtr<const FJsonObject>& Object, const TCHAR* Key)
    { const TArray<TSharedPtr<FJsonValue>>* Values = nullptr; return Object && Object->TryGetArrayField(Key, Values) ? *Values : TArray<TSharedPtr<FJsonValue>>(); }
    TSharedPtr<FJsonObject> Object(const TSharedPtr<const FJsonObject>& Parent, const TCHAR* Key)
    { const TSharedPtr<FJsonObject>* Value = nullptr; return Parent && Parent->TryGetObjectField(Key, Value) ? *Value : nullptr; }
}

FWarInterfaceCatalog FWarInterfaceCatalog::Parse(const TSharedPtr<const FJsonObject>& Root)
{
    FWarInterfaceCatalog Result;
    if (!Root) return Result;
    const auto Campaign = Object(Root, TEXT("campaign"));
    for (const auto& Value : Array(Campaign, TEXT("zones")))
    {
        const auto Row = Value->AsObject();
        FWarMapZone Zone;
        Zone.Id = String(Row, TEXT("id")); Zone.Name = String(Row, TEXT("name"));
        Zone.Realm = String(Row, TEXT("realm")); Zone.Lane = String(Row, TEXT("lane"));
        Zone.Tier = String(Row, TEXT("tier")); Zone.Role = String(Row, TEXT("nodeRole"));
        if (!Zone.Id.IsEmpty() && !Result.FindZone(Zone.Id)) Result.Zones.Add(MoveTemp(Zone));
    }
    for (const auto& Value : Array(Root, TEXT("maps")))
    {
        const auto Row = Value->AsObject(), Definition = Object(Row, TEXT("definition"));
        auto* Zone = Result.Zones.FindByPredicate([&](const auto& Entry) { return Entry.Id == String(Row, TEXT("id")); });
        if (!Zone || !Definition) continue;
        Zone->Size = FMath::Clamp(Number(Definition, TEXT("size"), 800), 1.0, 20000.0);
        for (const auto& Route : Array(Definition, TEXT("zoneTriggers")))
        {
            const FString Destination = String(Route->AsObject(), TEXT("targetZoneId"));
            if (Result.FindZone(Destination)) Zone->Destinations.AddUnique(Destination);
        }
        for (const auto& Path : Array(Definition, TEXT("paths")))
        {
            TArray<FVector2D> Points;
            for (const auto& Point : Array(Path->AsObject(), TEXT("points")))
                Points.Add(FVector2D(Number(Point->AsObject(), TEXT("x")), -Number(Point->AsObject(), TEXT("z"))));
            if (Points.Num() > 1) Zone->Paths.Add(MoveTemp(Points));
        }
        const TPair<const TCHAR*, const TCHAR*> Layers[] = {{TEXT("npcs"),TEXT("People")}, {TEXT("craftingStations"),TEXT("Crafting")},
            {TEXT("resourceNodes"),TEXT("Resources")}, {TEXT("enemies"),TEXT("Enemies")}, {TEXT("zoneTriggers"),TEXT("Exits")},
            {TEXT("rvrObjectives"),TEXT("Objectives")}, {TEXT("cityDistricts"),TEXT("Places")}, {TEXT("explorationPlaces"),TEXT("Places")}};
        for (const auto& Layer : Layers) for (const auto& Marker : Array(Definition, Layer.Key))
        {
            const auto Entry = Marker->AsObject(); if (!Entry) continue;
            FString Label = String(Entry, TEXT("label"));
            if (Label.IsEmpty()) Label = String(Entry, TEXT("name"));
            if (Label.IsEmpty()) Label = String(Entry, TEXT("id"));
            Zone->Markers.Add({String(Entry,TEXT("id")), Label, Layer.Value,
                FVector2D(Number(Entry,TEXT("x")), -Number(Entry,TEXT("z")))});
        }
    }
    const auto Wiki = Object(Root, TEXT("wiki"));
    for (const auto& Section : Array(Wiki, TEXT("sections")))
    {
        const auto Row = Section->AsObject();
        Result.Sections.Add({String(Row,TEXT("id")), String(Row,TEXT("title"))});
    }
    for (const auto& Value : Array(Wiki, TEXT("pages")))
    {
        const auto Row = Value->AsObject(); if (!Row) continue;
        FWarGuidePage Page;
        Page.Id = String(Row,TEXT("id")); Page.Title = String(Row,TEXT("title"));
        Page.Section = String(Row,TEXT("sectionId")); Page.Status = String(Row,TEXT("status"));
        Page.Text = String(Row,TEXT("subtitle")) + TEXT("\n\n");
        for (const auto& Paragraph : Array(Row,TEXT("body"))) Page.Text += Paragraph->AsString() + TEXT("\n\n");
        for (const auto& Detail : Array(Row,TEXT("details")))
            Page.Text += String(Detail->AsObject(),TEXT("label")) + TEXT(": ") + String(Detail->AsObject(),TEXT("value")) + TEXT("\n");
        for (const auto& Table : Array(Row,TEXT("tables")))
        {
            Page.Text += TEXT("\n") + String(Table->AsObject(),TEXT("title")) + TEXT("\n");
            TArray<FString> Columns;
            for (const auto& Column : Array(Table->AsObject(),TEXT("columns"))) Columns.Add(Column->AsString());
            for (const auto& TableRow : Array(Table->AsObject(),TEXT("rows")))
            {
                const auto Cells = Array(TableRow->AsObject(),TEXT("cells"));
                for (int32 Index = 0; Index < Cells.Num(); ++Index)
                    Page.Text += (Columns.IsValidIndex(Index) ? Columns[Index] + TEXT(": ") : FString()) + Cells[Index]->AsString() + TEXT("\n");
                Page.Text += TEXT("\n");
            }
        }
        Page.SearchText = (Page.Title + TEXT(" ") + Page.Text).ToLower();
        for (const auto& Tag : Array(Row,TEXT("tags"))) Page.SearchText += TEXT(" ") + Tag->AsString().ToLower();
        if (!Page.Id.IsEmpty()) Result.Pages.Add(MoveTemp(Page));
    }
    return Result;
}

const FWarMapZone* FWarInterfaceCatalog::FindZone(const FString& Id) const
{ return Zones.FindByPredicate([&Id](const auto& Zone) { return Zone.Id == Id; }); }
TArray<int32> FWarInterfaceCatalog::SearchGuide(const FString& Section, const FString& Query) const
{
    TArray<FString> Words; Query.TrimStartAndEnd().ToLower().ParseIntoArrayWS(Words);
    TArray<int32> Found;
    for (int32 Index = 0; Index < Pages.Num(); ++Index)
    {
        const auto& Page = Pages[Index];
        if (!Section.IsEmpty() && Page.Section != Section) continue;
        if (!Words.ContainsByPredicate([&Page](const auto& Word) { return !Page.SearchText.Contains(Word); })) Found.Add(Index);
    }
    return Found;
}
